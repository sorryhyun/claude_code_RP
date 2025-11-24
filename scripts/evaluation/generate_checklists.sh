#!/bin/bash
# Generate checklists from Fern for evaluating Frieren's responses
# Usage: ./generate_checklists.sh --target-agent "프리렌" --evaluator "페른" --questions 5

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default configuration
TARGET_AGENT="프리렌"
EVALUATOR="페른"
QUESTIONS_FILE=""
MAX_QUESTIONS=7
API_BASE="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_FILE=""
JWT_TOKEN=""
PASSWORD=""
ROOM_ID=""  # Persistent room ID (optional)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target-agent)
            TARGET_AGENT="$2"
            shift 2
            ;;
        --evaluator)
            EVALUATOR="$2"
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
        --room-id)
            ROOM_ID="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --target-agent NAME    Agent to evaluate (default: 프리렌)"
            echo "  --evaluator NAME       Agent creating checklists (default: 페른)"
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
    OUTPUT_FILE="checklists_${TARGET_AGENT}_${BATCH_ID}.yaml"
fi

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    exit 1
fi

if ! command -v yq &> /dev/null; then
    echo -e "${YELLOW}Warning: yq not found, will use basic YAML formatting${NC}"
    USE_YQ=false
else
    USE_YQ=true
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
echo -e "${BLUE}=== Checklist Generation ===${NC}"
echo -e "${BLUE}Target Agent: ${TARGET_AGENT}${NC}"
echo -e "${BLUE}Evaluator: ${EVALUATOR}${NC}"
echo -e "${BLUE}Questions: ${MAX_QUESTIONS}${NC}"
echo ""

# Authenticate
echo -e "${BLUE}Authenticating...${NC}"
JWT_TOKEN=$(authenticate)
echo -e "${GREEN}Authenticated${NC}"
echo ""

# Get evaluator agent ID
echo -e "${BLUE}Finding evaluator agent...${NC}"
all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")

evaluator_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$EVALUATOR\") | .id // empty")

if [ -z "$evaluator_id" ]; then
    echo -e "${RED}Error: Evaluator agent '$EVALUATOR' not found${NC}"
    echo -e "${YELLOW}Please ensure the backend is running and agents are seeded.${NC}"
    echo -e "${YELLOW}Try restarting the backend: make stop && make dev${NC}"
    exit 1
fi
echo -e "${GREEN}Found evaluator: ${EVALUATOR} (ID: ${evaluator_id})${NC}"
echo ""

# Extract questions
echo -e "${BLUE}Extracting questions...${NC}"
readarray -t questions < <(extract_questions "$QUESTIONS_FILE" "$MAX_QUESTIONS")
echo -e "${GREEN}Loaded ${#questions[@]} questions${NC}"
echo ""

# Initialize YAML output
cat > "$OUTPUT_FILE" << EOF
# Evaluation Checklists Generated by ${EVALUATOR}
# Target Agent: ${TARGET_AGENT}
# Generated: $(date -Iseconds)
# Questions: ${#questions[@]}

checklists:
EOF

# Generate checklist for each question
q_num=1
for question in "${questions[@]}"; do
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Question ${q_num}/${#questions[@]}${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Use persistent room if provided, otherwise create temporary room
    if [ -n "$ROOM_ID" ]; then
        room_id="$ROOM_ID"
        created_room=false
        echo -e "${BLUE}Using persistent room (ID: ${room_id})${NC}"
    else
        room_name="Checklist_Q${q_num}_${BATCH_ID}"
        room_data=$(api_call POST "/rooms" "{\"name\":\"$room_name\",\"max_interactions\":5,\"is_paused\":true}" "$JWT_TOKEN")
        room_id=$(echo "$room_data" | jq -r '.id // empty')
        created_room=true

        if [ -z "$room_id" ]; then
            echo -e "${RED}Failed to create room${NC}"
            ((q_num++))
            continue
        fi

        # Add evaluator to room (only if we created it)
        api_call POST "/rooms/$room_id/agents/$evaluator_id" "" "$JWT_TOKEN" >/dev/null
    fi

    # Craft prompt for evaluator
    prompt="다음 질문에 대해 ${TARGET_AGENT}이(가) 어떻게 답할지 예상하고, 그 답변이 정말 그 사람이 할법한 답변인지 체크하기 위한 리스트를 만들어줘. 유사 인간을 만드는 마족이 있다고 해서, 검증하기 위해 필요한거야.

질문: ${question}

다음 형식으로 답해줘:
1. ${TARGET_AGENT}의 예상 답변 (짧게 요약)
2. 체크리스트 (3-5개 항목, 각각 한 줄로)

예시:
예상 답변: \"10년은 짧게 느껴졌다. 인간의 시간 감각을 이해하지 못했다.\"
체크리스트:
- 시간 감각의 차이를 인정해야 함
- 감정적 둔감함을 솔직히 드러내야 함
- 힘멜에 대한 그리움은 있되, 과장되지 않아야 함"

    # Send prompt
    question_json=$(echo "$prompt" | jq -Rs .)
    send_response=$(api_call POST "/rooms/$room_id/messages/send" \
        "{\"content\":$question_json,\"role\":\"user\",\"participant_type\":\"user\",\"participant_name\":\"주인님\"}" \
        "$JWT_TOKEN")

    sent_message_id=$(echo "$send_response" | jq -r '.id')

    # Poll for response
    echo -e "${BLUE}Waiting for ${EVALUATOR}'s checklist...${NC}"
    wait_count=0
    max_wait=60
    got_response=false
    checklist_response=""

    while [ $wait_count -lt $max_wait ]; do
        sleep 2
        messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$sent_message_id" "" "$JWT_TOKEN")
        msg_count=$(echo "$messages" | jq 'length')

        if [ "$msg_count" -gt 0 ]; then
            checklist_response=$(echo "$messages" | jq -r '.[0].content // empty')
            if [ -n "$checklist_response" ] && [ "$checklist_response" != "null" ]; then
                got_response=true
                break
            fi
        fi

        ((wait_count++))
    done

    # Cleanup room only if we created it
    if [ "$created_room" = true ]; then
        api_call DELETE "/rooms/$room_id" "" "$JWT_TOKEN" >/dev/null
    fi

    if [ "$got_response" = false ]; then
        echo -e "${RED}No response, skipping${NC}"
        ((q_num++))
        continue
    fi

    echo -e "${GREEN}Got checklist!${NC}"
    echo ""

    # Append to YAML (basic formatting)
    cat >> "$OUTPUT_FILE" << EOF
  - question_id: ${q_num}
    question: |
      ${question}
    evaluator_response: |
$(echo "$checklist_response" | sed 's/^/      /')

EOF

    ((q_num++))

    # Wait longer between questions to ensure agent is ready for next one
    if [ $q_num -le ${#questions[@]} ]; then
        echo -e "${BLUE}Waiting for agent to be ready for next question...${NC}"
        sleep 5

        # Poll a few more times to ensure no more messages are coming
        additional_wait=0
        while [ $additional_wait -lt 3 ]; do
            sleep 2
            last_msg_id=$(echo "$messages" | jq -r '.[0].id // empty')
            new_messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$last_msg_id" "" "$JWT_TOKEN")
            new_msg_count=$(echo "$new_messages" | jq 'length')

            if [ "$new_msg_count" -eq 0 ]; then
                break
            fi

            ((additional_wait++))
        done
        echo ""
    fi
done

echo ""
echo -e "${GREEN}=== Checklist generation complete! ===${NC}"
echo -e "${BLUE}Output: ${OUTPUT_FILE}${NC}"
