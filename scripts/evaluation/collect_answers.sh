#!/bin/bash
# Collect answers from target agent (e.g., Frieren)
# Usage: ./collect_answers.sh --target-agent "프리렌" --questions 5

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default configuration
TARGET_AGENT="프리렌"
QUESTIONS_FILE=""
MAX_QUESTIONS=5
API_BASE="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_FILE=""
JWT_TOKEN=""
PASSWORD=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target-agent)
            TARGET_AGENT="$2"
            shift 2
            ;;
        --questions)
            MAX_QUESTIONS="$2"
            shift 2
            ;;
        --questions-file)
            QUESTIONS_FILE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --password)
            PASSWORD="$2"
            shift 2
            ;;
        --token)
            JWT_TOKEN="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --target-agent NAME    Agent to collect answers from (default: 프리렌)"
            echo "  --questions N          Number of questions (default: 5)"
            echo "  --questions-file FILE  Path to questions file"
            echo "  --output FILE          Output YAML file"
            echo "  --password PASS        Authentication password"
            echo "  --token TOKEN          JWT token (skip auth)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Load from .env if available
if [ -f ".env" ] && [ -z "$JWT_TOKEN" ]; then
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [ -z "$PASSWORD" ]; then
        PASSWORD=$(grep '^CHITCHATS_PASSWORD=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    fi
fi

# Set default questions file
if [ -z "$QUESTIONS_FILE" ]; then
    QUESTIONS_FILE="agent_questions/${TARGET_AGENT}.md"
fi

# Set default output file
if [ -z "$OUTPUT_FILE" ]; then
    BATCH_ID=$(date +%s)
    OUTPUT_FILE="answers_${TARGET_AGENT}_${BATCH_ID}.yaml"
fi

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    exit 1
fi

# Check questions file exists
if [ ! -f "$QUESTIONS_FILE" ]; then
    echo -e "${RED}Error: Questions file not found: $QUESTIONS_FILE${NC}"
    exit 1
fi

# API helper function
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

# Authentication
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
        exit 1
    fi

    echo "$token"
}

# Extract questions from markdown
extract_questions() {
    local file=$1
    local max_q=$2
    local questions=()
    local current_q=""
    local q_count=0

    while IFS= read -r line; do
        if [[ $line =~ ^[0-9]+\.[[:space:]](.+) ]]; then
            if [ $q_count -ge $max_q ]; then
                break
            fi
            if [ -n "$current_q" ]; then
                questions+=("$current_q")
            fi
            current_q="${BASH_REMATCH[1]}"
            ((q_count++))
        elif [[ -z "$line" || $line =~ ^# ]]; then
            continue
        fi
    done < "$file"

    if [ -n "$current_q" ] && [ $q_count -le $max_q ]; then
        questions+=("$current_q")
    fi

    printf '%s\n' "${questions[@]}"
}

# Main script
echo -e "${BLUE}=== Answer Collection ===${NC}"
echo -e "${BLUE}Target Agent: ${TARGET_AGENT}${NC}"
echo -e "${BLUE}Questions: ${MAX_QUESTIONS}${NC}"
echo ""

# Authenticate
echo -e "${BLUE}Authenticating...${NC}"
JWT_TOKEN=$(authenticate)
echo -e "${GREEN}Authenticated${NC}"
echo ""

# Get target agent ID
echo -e "${BLUE}Finding target agent...${NC}"
all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")

# Debug: Show all available agents
echo -e "${YELLOW}Available agents:${NC}"
echo "$all_agents" | jq -r '.[] | "  - \(.name) (ID: \(.id))"'
echo ""

target_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$TARGET_AGENT\") | .id // empty")

if [ -z "$target_id" ]; then
    echo -e "${RED}Error: Target agent '$TARGET_AGENT' not found${NC}"
    echo -e "${YELLOW}Please ensure the backend is running and agents are seeded.${NC}"
    echo -e "${YELLOW}Try restarting the backend: make stop && make dev${NC}"
    exit 1
fi
echo -e "${GREEN}Found agent: ${TARGET_AGENT} (ID: ${target_id})${NC}"
echo ""

# Extract questions
echo -e "${BLUE}Extracting questions...${NC}"
readarray -t questions < <(extract_questions "$QUESTIONS_FILE" "$MAX_QUESTIONS")
echo -e "${GREEN}Loaded ${#questions[@]} questions${NC}"
echo ""

# Initialize YAML output
cat > "$OUTPUT_FILE" << EOF
# Answers from ${TARGET_AGENT}
# Generated: $(date -Iseconds)
# Questions: ${#questions[@]}

answers:
EOF

# Collect answer for each question
q_num=1
for question in "${questions[@]}"; do
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Question ${q_num}/${#questions[@]}${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Create paused room
    room_name="Answer_Q${q_num}_$(date +%s)"
    room_data=$(api_call POST "/rooms" "{\"name\":\"$room_name\",\"max_interactions\":5,\"is_paused\":true}" "$JWT_TOKEN")
    room_id=$(echo "$room_data" | jq -r '.id // empty')

    if [ -z "$room_id" ]; then
        echo -e "${RED}Failed to create room${NC}"
        ((q_num++))
        continue
    fi

    # Add target agent to room
    api_call POST "/rooms/$room_id/agents/$target_id" "" "$JWT_TOKEN" >/dev/null

    # Send question
    question_json=$(echo "$question" | jq -Rs .)
    send_response=$(api_call POST "/rooms/$room_id/messages/send" \
        "{\"content\":$question_json,\"role\":\"user\",\"participant_type\":\"user\"}" \
        "$JWT_TOKEN")

    sent_message_id=$(echo "$send_response" | jq -r '.id')

    echo "Q: ${question}"
    echo ""

    # Poll for response
    echo -e "${BLUE}Waiting for ${TARGET_AGENT}'s answer...${NC}"
    wait_count=0
    max_wait=60
    got_response=false
    agent_answer=""
    thinking_text=""

    while [ $wait_count -lt $max_wait ]; do
        sleep 2
        messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$sent_message_id" "" "$JWT_TOKEN")
        msg_count=$(echo "$messages" | jq 'length')

        if [ "$msg_count" -gt 0 ]; then
            agent_answer=$(echo "$messages" | jq -r '.[0].content // empty')
            thinking_text=$(echo "$messages" | jq -r '.[0].thinking // empty')
            if [ -n "$agent_answer" ] && [ "$agent_answer" != "null" ]; then
                got_response=true
                break
            fi
        fi

        ((wait_count++))
    done

    if [ "$got_response" = false ]; then
        echo -e "${RED}No response, skipping${NC}"
        # Cleanup room before continuing
        api_call DELETE "/rooms/$room_id" "" "$JWT_TOKEN" >/dev/null
        ((q_num++))
        continue
    fi

    echo -e "${GREEN}Got answer!${NC}"
    echo ""

    # Show thinking if available
    if [ -n "$thinking_text" ] && [ "$thinking_text" != "null" ] && [ "$thinking_text" != "" ]; then
        echo -e "${BLUE}[Thinking]${NC}"
        echo "$thinking_text"
        echo ""
    fi

    echo -e "${BLUE}[Answer]${NC}"
    echo "$agent_answer"
    echo ""

    # Append to YAML
    cat >> "$OUTPUT_FILE" << EOF
  - question_id: ${q_num}
    question: |
      ${question}
    thinking: |
$(echo "$thinking_text" | sed 's/^/      /')
    answer: |
$(echo "$agent_answer" | sed 's/^/      /')

EOF

    # Cleanup room (delete after getting answer)
    api_call DELETE "/rooms/$room_id" "" "$JWT_TOKEN" >/dev/null

    ((q_num++))

    # Brief pause between questions
    sleep 1
done

echo ""
echo -e "${GREEN}=== Answer collection complete! ===${NC}"
echo -e "${BLUE}Output: ${OUTPUT_FILE}${NC}"
