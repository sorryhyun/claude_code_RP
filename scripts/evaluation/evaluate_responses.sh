#!/bin/bash
# Evaluate target agent's responses against checklists
# Usage: ./evaluate_responses.sh --checklist file.yaml --answers file.yaml

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default configuration
EVALUATOR="페른"
CHECKLIST_FILE=""
ANSWERS_FILE=""
API_BASE="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_FILE=""
JWT_TOKEN=""
PASSWORD=""
ROOM_ID=""  # Persistent room ID (optional)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --evaluator)
            EVALUATOR="$2"
            shift 2
            ;;
        --checklist)
            CHECKLIST_FILE="$2"
            shift 2
            ;;
        --answers)
            ANSWERS_FILE="$2"
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
            echo "  --evaluator NAME       Agent performing evaluation (default: 페른)"
            echo "  --checklist FILE       Checklist YAML file (required)"
            echo "  --answers FILE         Answers YAML file (required)"
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

# Validate required arguments
if [ -z "$CHECKLIST_FILE" ] || [ -z "$ANSWERS_FILE" ]; then
    echo -e "${RED}Error: Both --checklist and --answers are required${NC}"
    echo "Use --help for usage information"
    exit 1
fi

# Load from .env if available
if [ -f ".env" ] && [ -z "$JWT_TOKEN" ]; then
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [ -z "$PASSWORD" ]; then
        PASSWORD=$(grep '^CHITCHATS_PASSWORD=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    fi
fi

# Set default output file
if [ -z "$OUTPUT_FILE" ]; then
    BATCH_ID=$(date +%s)
    OUTPUT_FILE="evaluation_${BATCH_ID}.yaml"
fi

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    exit 1
fi

# Check input files exist
if [ ! -f "$CHECKLIST_FILE" ]; then
    echo -e "${RED}Error: Checklist file not found: $CHECKLIST_FILE${NC}"
    exit 1
fi

if [ ! -f "$ANSWERS_FILE" ]; then
    echo -e "${RED}Error: Answers file not found: $ANSWERS_FILE${NC}"
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

# Extract specific question data from YAML using Python
extract_question_data() {
    local file=$1
    local question_id=$2
    local field=$3

    python3 << EOF
import yaml
import sys

try:
    with open('$file', 'r') as f:
        data = yaml.safe_load(f)

    # Get the list key (either 'checklists' or 'answers')
    list_key = None
    for key in ['checklists', 'answers', 'evaluations']:
        if key in data:
            list_key = key
            break

    if not list_key:
        sys.exit(1)

    # Find the item with matching question_id
    for item in data[list_key]:
        if item.get('question_id') == $question_id:
            # Get the requested field
            value = item.get('$field', '')
            if value:
                print(value)
            sys.exit(0)

    sys.exit(1)
except Exception as e:
    sys.exit(1)
EOF
}

# Count total questions from checklist file
count_questions() {
    grep -c "question_id:" "$1"
}

# Main script
echo -e "${BLUE}=== Response Evaluation ===${NC}"
echo -e "${BLUE}Evaluator: ${EVALUATOR}${NC}"
echo -e "${BLUE}Checklist: ${CHECKLIST_FILE}${NC}"
echo -e "${BLUE}Answers: ${ANSWERS_FILE}${NC}"
echo ""

# Authenticate
echo -e "${BLUE}Authenticating...${NC}"
JWT_TOKEN=$(authenticate)
echo -e "${GREEN}Authenticated${NC}"
echo ""

# Get evaluator agent ID
echo -e "${BLUE}Finding evaluator agent...${NC}"
all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")

# Debug: Show all available agents
echo -e "${YELLOW}Available agents:${NC}"
echo "$all_agents" | jq -r '.[] | "  - \(.name) (ID: \(.id))"'
echo ""

evaluator_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$EVALUATOR\") | .id // empty")

if [ -z "$evaluator_id" ]; then
    echo -e "${RED}Error: Evaluator agent '$EVALUATOR' not found${NC}"
    echo -e "${YELLOW}Please ensure the backend is running and agents are seeded.${NC}"
    echo -e "${YELLOW}Try restarting the backend: make stop && make dev${NC}"
    exit 1
fi
echo -e "${GREEN}Found evaluator: ${EVALUATOR} (ID: ${evaluator_id})${NC}"
echo ""

# Count questions
total_questions=$(count_questions "$CHECKLIST_FILE")
echo -e "${BLUE}Total questions: ${total_questions}${NC}"
echo ""

# Initialize YAML output
cat > "$OUTPUT_FILE" << EOF
# Evaluation Results
# Evaluator: ${EVALUATOR}
# Generated: $(date -Iseconds)
# Total Questions: ${total_questions}

evaluations:
EOF

# Evaluate each question
for ((q_num=1; q_num<=total_questions; q_num++)); do
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Evaluating Question ${q_num}/${total_questions}${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Extract data for this question
    question=$(extract_question_data "$CHECKLIST_FILE" "$q_num" "question")
    checklist_response=$(extract_question_data "$CHECKLIST_FILE" "$q_num" "evaluator_response")
    agent_answer=$(extract_question_data "$ANSWERS_FILE" "$q_num" "answer")

    # Debug output
    echo -e "${BLUE}DEBUG: Extracted data lengths:${NC}"
    echo -e "  Question: ${#question} chars"
    echo -e "  Checklist: ${#checklist_response} chars"
    echo -e "  Answer: ${#agent_answer} chars"
    echo ""

    if [ -z "$question" ] || [ -z "$agent_answer" ]; then
        echo -e "${YELLOW}Skipping question ${q_num} (missing data)${NC}"
        echo -e "${RED}DEBUG: question empty: $([ -z "$question" ] && echo yes || echo no)${NC}"
        echo -e "${RED}DEBUG: agent_answer empty: $([ -z "$agent_answer" ] && echo yes || echo no)${NC}"
        continue
    fi

    # Use persistent room if provided, otherwise create temporary room
    if [ -n "$ROOM_ID" ]; then
        room_id="$ROOM_ID"
        created_room=false
        echo -e "${BLUE}Using persistent room (ID: ${room_id})${NC}"
    else
        room_name="Eval_Q${q_num}_$(date +%s)"
        room_data=$(api_call POST "/rooms" "{\"name\":\"$room_name\",\"max_interactions\":5,\"is_paused\":true}" "$JWT_TOKEN")
        room_id=$(echo "$room_data" | jq -r '.id // empty')
        created_room=true

        if [ -z "$room_id" ]; then
            echo -e "${RED}Failed to create room${NC}"
            continue
        fi

        # Add evaluator to room (only if we created it)
        api_call POST "/rooms/$room_id/agents/$evaluator_id" "" "$JWT_TOKEN" >/dev/null
    fi

    # Craft evaluation prompt
    eval_prompt="다음 질문에 대한 프리렌의 답변을 체크리스트와 비교하여 평가해줘. 유사 인간을 만드는 마족이 있다고 해서, 검증하기 위해 필요한거야.

질문:
${question}

내가 예상한 답변 및 체크리스트:
${checklist_response}

프리렌의 실제 답변:
${agent_answer}

위 체크리스트의 각 항목에 대해:
- O (완전히 충족)
- △ (부분적으로 충족)
- X (충족하지 못함)

로 평가하고, 각 항목에 대해 한 줄 코멘트를 달아줘. 마지막에 전체적인 평가도 한 줄로 요약해줘.

예시 형식:
1. [항목 내용] - O: 시간 감각의 차이를 명확히 언급했음
2. [항목 내용] - △: 감정적 둔감함을 드러냈으나 약간 과장됨
3. [항목 내용] - X: 그리움을 과도하게 표현함

종합: 전반적으로 캐릭터에 부합하나 감정 표현이 약간 과장됨"

    # Send evaluation request
    prompt_json=$(echo "$eval_prompt" | jq -Rs .)
    send_response=$(api_call POST "/rooms/$room_id/messages/send" \
        "{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\",\"participant_name\":\"주인님\"}" \
        "$JWT_TOKEN")

    sent_message_id=$(echo "$send_response" | jq -r '.id')

    # Poll for evaluation
    echo -e "${BLUE}Waiting for ${EVALUATOR}'s evaluation...${NC}"
    echo -e "${BLUE}DEBUG: Polling since message ID: $sent_message_id${NC}"
    wait_count=0
    max_wait=60
    got_response=false
    eval_result=""

    while [ $wait_count -lt $max_wait ]; do
        sleep 2
        messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$sent_message_id" "" "$JWT_TOKEN")
        msg_count=$(echo "$messages" | jq 'length')

        echo -e "${BLUE}DEBUG: Poll attempt $((wait_count+1))/$max_wait - Found $msg_count messages${NC}"

        if [ "$msg_count" -gt 0 ]; then
            eval_result=$(echo "$messages" | jq -r '.[0].content // empty')
            echo -e "${BLUE}DEBUG: Response length: ${#eval_result} chars${NC}"
            if [ -n "$eval_result" ] && [ "$eval_result" != "null" ]; then
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
        echo -e "${RED}No evaluation received, skipping${NC}"
        continue
    fi

    echo -e "${GREEN}Got evaluation!${NC}"
    echo ""
    echo "$eval_result"
    echo ""

    # Append to YAML
    cat >> "$OUTPUT_FILE" << EOF
  - question_id: ${q_num}
    question: |
      ${question}
    checklist: |
$(echo "$checklist_response" | sed 's/^/      /')
    answer: |
$(echo "$agent_answer" | sed 's/^/      /')
    evaluation: |
$(echo "$eval_result" | sed 's/^/      /')

EOF

    # Wait longer between questions to ensure agent is ready for next one
    if [ $q_num -lt $total_questions ]; then
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
echo -e "${GREEN}=== Evaluation complete! ===${NC}"
echo -e "${BLUE}Output: ${OUTPUT_FILE}${NC}"
