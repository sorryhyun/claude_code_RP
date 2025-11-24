#!/bin/bash
# Test agent capabilities by asking them questions sequentially
# Multiple agents are tested in parallel
# Run with: chmod +x test_agent_questions.sh && ./test_agent_questions.sh

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Load configuration from .env if it exists
if [ -f ".env" ]; then
    # Load JWT token
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    # Load password if available
    PASSWORD=$(grep '^CHITCHATS_PASSWORD=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
fi

# Configuration
QUESTIONS_PER_AGENT=${1:-10}  # Questions to ask each agent (default: 10)
API_BASE="${BACKEND_URL:-http://localhost:8000}"
PASSWORD="${PASSWORD:-${CHITCHATS_PASSWORD:-}}"  # From .env, env var, or will prompt
JWT_TOKEN="${JWT_TOKEN:-}"

# Agents to test (can be specified as arguments after question count)
# Example: ./test_agent_questions.sh 10 봇치 프리렌 치즈루 코베니
[ $# -gt 0 ] && shift  # Remove first argument (question count) if present
if [ $# -gt 0 ]; then
    AGENTS_TO_TEST=("$@")
else
    AGENTS_TO_TEST=("페른" "프리렌")
fi

# Generate unique timestamp prefix for this batch
BATCH_ID=$(date +%s)

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    echo "Install with: sudo apt-get install jq (Debian/Ubuntu) or brew install jq (macOS)"
    exit 1
fi

# Function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_header=$4

    local args=(-s -X "$method" "$API_BASE$endpoint")

    if [ -n "$auth_header" ]; then
        args+=(-H "X-API-Key: $auth_header")
    fi

    if [ -n "$data" ]; then
        args+=(-H "Content-Type: application/json" -d "$data")
    fi

    curl "${args[@]}"
}

# Function to authenticate and get JWT token
authenticate() {
    if [ -n "$JWT_TOKEN" ]; then
        echo -e "${YELLOW}Using existing JWT token...${NC}" >&2
        echo "$JWT_TOKEN"
        return
    fi

    if [ -z "$PASSWORD" ]; then
        echo -e "${YELLOW}Enter password:${NC}" >&2
        read -s PASSWORD
        echo "" >&2
    fi

    local response=$(api_call POST "/auth/login" "{\"password\":\"$PASSWORD\"}" "")
    local token=$(echo "$response" | jq -r '.api_key // empty')

    if [ -z "$token" ]; then
        echo -e "${RED}Authentication failed${NC}" >&2
        echo "$response" | jq '.' 2>/dev/null || echo "$response" >&2
        exit 1
    fi

    echo "$token"
}

# Function to log with colors to terminal, plain text to file
log() {
    local message="$1"
    local output_file="$2"

    # Print with colors to terminal
    echo -e "$message"

    # Strip ANSI codes and write to file
    if [ -n "$output_file" ]; then
        echo -e "$message" | sed 's/\x1b\[[0-9;]*m//g' >> "$output_file"
    fi
}

# Function to extract questions from markdown file
extract_questions() {
    local file=$1
    local max_questions=$2

    # Extract questions (simple numbered format)
    local questions=()
    local current_q=""
    local q_count=0

    while IFS= read -r line; do
        # Match question number (e.g., "1. Question text...")
        if [[ $line =~ ^[0-9]+\.[[:space:]](.+) ]]; then
            if [ $q_count -ge $max_questions ]; then
                break
            fi
            if [ -n "$current_q" ]; then
                questions+=("$current_q")
            fi
            current_q="${BASH_REMATCH[1]}"
            ((q_count++))
        # Skip empty lines and headers
        elif [[ -z "$line" || $line =~ ^# ]]; then
            continue
        fi
    done < "$file"

    # Add last question
    if [ -n "$current_q" ] && [ $q_count -le $max_questions ]; then
        questions+=("$current_q")
    fi

    # Print array as lines
    printf '%s\n' "${questions[@]}"
}

# Function to test a single agent sequentially
test_agent() {
    local agent_name=$1
    local questions_file=$2
    local max_questions=$3
    local token=$4
    local output_file=$5

    log "${GREEN}[${agent_name}] Starting test${NC}" "$output_file"

    # Get agent ID once
    local all_agents=$(api_call GET "/agents" "" "$token")
    local agent_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$agent_name\") | .id // empty")

    if [ -z "$agent_id" ]; then
        log "${RED}[${agent_name}] Agent not found${NC}" "$output_file"
        return 1
    fi

    # Extract questions
    readarray -t questions < <(extract_questions "$questions_file" "$max_questions")

    log "\n${BLUE}[${agent_name}] Asking ${#questions[@]} questions...${NC}\n" "$output_file"

    # Ask each question in a separate room
    local q_num=1
    for question in "${questions[@]}"; do
        log "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" "$output_file"
        log "${GREEN}[${agent_name}] Question ${q_num}/${#questions[@]}${NC}" "$output_file"
        log "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" "$output_file"

        # Create new room for this question (paused to exclude from background scheduler)
        local room_name="Q${q_num}_${agent_name}_${BATCH_ID}"
        local room_data=$(api_call POST "/rooms" "{\"name\":\"$room_name\",\"max_interactions\":5,\"is_paused\":true}" "$token")
        local room_id=$(echo "$room_data" | jq -r '.id // empty')

        if [ -z "$room_id" ]; then
            log "${RED}[${agent_name}] Failed to create room for Q${q_num}${NC}\n" "$output_file"
            ((q_num++))
            continue
        fi

        # Add agent to room
        local add_response=$(api_call POST "/rooms/$room_id/agents/$agent_id" "" "$token")
        if ! echo "$add_response" | jq -e '.id' >/dev/null; then
            log "${RED}[${agent_name}] Failed to add agent to room${NC}\n" "$output_file"
            api_call DELETE "/rooms/$room_id" "" "$token" >/dev/null
            ((q_num++))
            continue
        fi

        # Escape question for JSON
        local question_json=$(echo "$question" | jq -Rs .)

        # Send question as user message
        local send_response=$(api_call POST "/rooms/$room_id/messages/send" \
            "{\"content\":$question_json,\"role\":\"user\",\"participant_type\":\"user\"}" \
            "$token")

        if ! echo "$send_response" | jq -e '.id' >/dev/null; then
            log "${RED}[${agent_name}] Failed to send question${NC}\n" "$output_file"
            api_call DELETE "/rooms/$room_id" "" "$token" >/dev/null
            ((q_num++))
            continue
        fi

        log "Q: ${question}\n" "$output_file"

        # Get the message ID of the question we just sent
        local sent_message_id=$(echo "$send_response" | jq -r '.id')

        # Poll for agent response (up to 120 seconds)
        local wait_count=0
        local max_wait=60  # 60 * 2 seconds = 120 seconds
        local got_response=false

        while [ $wait_count -lt $max_wait ]; do
            sleep 2

            # Poll for new messages since our question
            local messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$sent_message_id" "" "$token")

            # Check if we got new messages
            local msg_count=$(echo "$messages" | jq 'length')

            if [ "$msg_count" -gt 0 ]; then
                # Get agent's response and thinking text
                local agent_response=$(echo "$messages" | jq -r '.[0].content // empty')
                local thinking_text=$(echo "$messages" | jq -r '.[0].thinking // empty')

                if [ -n "$agent_response" ] && [ "$agent_response" != "null" ]; then
                    # Show thinking text if available (disabled)
                    # if [ -n "$thinking_text" ] && [ "$thinking_text" != "null" ] && [ "$thinking_text" != "" ]; then
                    #     log "${BLUE}[Thinking]${NC}\n${thinking_text}\n" "$output_file"
                    # fi

                    # Show response
                    log "${BLUE}A:${NC} ${agent_response}\n" "$output_file"
                    got_response=true
                    break
                fi
            fi

            ((wait_count++))
        done

        if [ "$got_response" = false ]; then
            log "${RED}[${agent_name}] No response after 120s, moving to next question${NC}\n" "$output_file"
        fi

        # Delete the room (cleanup)
        api_call DELETE "/rooms/$room_id" "" "$token" >/dev/null

        ((q_num++))

        # Brief pause between questions
        sleep 1
    done

    log "\n${GREEN}[${agent_name}] Test completed!${NC}\n" "$output_file"
}

# Main script
echo -e "${BLUE}=== Agent Question Testing ===${NC}"
echo -e "${BLUE}Batch ID: ${BATCH_ID}${NC}"
echo -e "${BLUE}Testing ${#AGENTS_TO_TEST[@]} agents in parallel: ${AGENTS_TO_TEST[*]}${NC}"
echo -e "${BLUE}Questions per agent: ${QUESTIONS_PER_AGENT}${NC}"
echo ""

# Authenticate
echo -e "${BLUE}Authenticating...${NC}"
JWT_TOKEN=$(authenticate)
echo -e "${GREEN}Authenticated successfully${NC}"
echo ""

# Launch tests for agents in parallel
echo -e "${BLUE}Starting agent tests...${NC}"
echo ""

agent_count=0
for agent_name in "${AGENTS_TO_TEST[@]}"; do
    # Find agent directory (could be in agents/ directly or in a group subdirectory)
    agent_dir=""
    if [ -f "agents/${agent_name}/in_a_nutshell.md" ]; then
        agent_dir="agents/${agent_name}"
    else
        # Search in group subdirectories
        agent_dir=$(find agents -type f -path "*/${agent_name}/in_a_nutshell.md" -exec dirname {} \; | head -1)
    fi

    if [ -z "$agent_dir" ]; then
        echo -e "${YELLOW}Warning: Agent '${agent_name}' not found in agents/, skipping${NC}"
        continue
    fi

    # Check if question file exists
    questions_file="agent_questions/${agent_name}.md"
    if [ ! -f "$questions_file" ]; then
        echo -e "${YELLOW}Warning: Questions file '${questions_file}' not found, skipping${NC}"
        continue
    fi

    # Output file
    output_file="test_${agent_name}_${BATCH_ID}.txt"

    # Launch agent test in background
    test_agent "$agent_name" "$questions_file" "$QUESTIONS_PER_AGENT" "$JWT_TOKEN" "$output_file" &

    # Stagger starts
    sleep 2

    ((agent_count++))
done

if [ $agent_count -eq 0 ]; then
    echo -e "${RED}No valid agents found to test${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=== All ${agent_count} agent tests running in parallel ===${NC}"
echo -e "${BLUE}Waiting for completion...${NC}"
echo ""

# Wait for all background jobs
wait

echo ""
echo -e "${GREEN}=== All tests completed! ===${NC}"
echo ""
echo -e "${BLUE}Generated transcripts:${NC}"
ls -lh test_*_${BATCH_ID}.txt 2>/dev/null || echo "No files found"
