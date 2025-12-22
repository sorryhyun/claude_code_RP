#!/bin/bash
# Parallel evaluation with single session per question
# Each question runs in its own evaluator session: checklist -> answer -> evaluate
# Usage: ./evaluate_parallel.sh --target-agent "프리렌" --evaluator "페른" --questions 5

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# Default configuration
TARGET_AGENT="프리렌"
EVALUATOR="페른"
MAX_QUESTIONS=7
PARALLEL_LIMIT=7
QUESTIONS_FILE=""
PASSWORD=""
JWT_TOKEN=""
API_BASE="${BACKEND_URL:-http://localhost:8000}"
SPEAKER="user"  # "user" or character name

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
        --parallel-limit)
            PARALLEL_LIMIT="$2"
            shift 2
            ;;
        --questions-file)
            QUESTIONS_FILE="$2"
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
        --speaker)
            SPEAKER="$2"
            shift 2
            ;;
        --help)
            echo "Parallel Agent Evaluation (Single Session per Question)"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Each question runs in its own evaluator session:"
            echo "  1. Generate checklist (evaluator predicts expected response)"
            echo "  2. Collect answer (target agent responds)"
            echo "  3. Evaluate (same session - evaluator checks answer against checklist)"
            echo ""
            echo "All questions run in parallel."
            echo ""
            echo "Options:"
            echo "  --target-agent NAME    Agent to evaluate (default: 프리렌)"
            echo "  --evaluator NAME       Agent performing evaluation (default: 페른)"
            echo "  --questions N          Number of questions (default: 7)"
            echo "  --parallel-limit N     Max parallel evaluations per batch (default: 5)"
            echo "  --questions-file FILE  Path to questions file"
            echo "  --password PASS        Authentication password"
            echo "  --token TOKEN          JWT token (skip auth)"
            echo "  --speaker NAME         Who asks the question: 'user' or character name (default: user)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set default questions file
if [ -z "$QUESTIONS_FILE" ]; then
    QUESTIONS_FILE="agent_questions/${TARGET_AGENT}.md"
fi

# Check questions file exists
if [ ! -f "$QUESTIONS_FILE" ]; then
    echo -e "${RED}Error: Questions file not found: $QUESTIONS_FILE${NC}"
    exit 1
fi

# Generate batch ID
BATCH_ID=$(date +%s)

# Create output directory
mkdir -p test_res

# Load from .env if available
if [ -f ".env" ] && [ -z "$JWT_TOKEN" ]; then
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [ -z "$PASSWORD" ]; then
        PASSWORD=$(grep '^CHITCHATS_PASSWORD=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    fi
fi

# API helper function with retry logic
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_header=$4
    local max_retries=5
    local retry_delay=1

    local args=(-s -X "$method" "$API_BASE$endpoint")

    if [ -n "$auth_header" ]; then
        args+=(-H "X-API-Key: $auth_header")
    fi

    if [ -n "$data" ]; then
        args+=(-H "Content-Type: application/json" -d "$data")
    fi

    # Retry logic for database lock issues
    for ((attempt=1; attempt<=max_retries; attempt++)); do
        local response=$(curl "${args[@]}" 2>/dev/null)

        # Check if response contains error about database lock
        if echo "$response" | grep -qi "database.*lock\|locked\|busy"; then
            if [ $attempt -lt $max_retries ]; then
                sleep $retry_delay
                retry_delay=$((retry_delay * 2))
                continue
            fi
        fi

        echo "$response"
        return 0
    done

    echo "$response"
}

# Authentication
authenticate() {
    if [ -n "$JWT_TOKEN" ]; then
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

# Function to evaluate a single question (runs in its own process)
# All three steps happen in the SAME evaluator session
evaluate_single_question() {
    local q_num=$1
    local question=$2
    local target_agent=$3
    local evaluator=$4
    local evaluator_id=$5
    local target_id=$6
    local token=$7
    local batch_id=$8
    local temp_output=$9
    local speaker=${10}

    # Create evaluator room (persistent for this question)
    # Include evaluator name to avoid collision when running parallel cross-evaluations
    local eval_room_name="Eval_${evaluator}_Q${q_num}_${batch_id}"
    local eval_room_data=$(api_call POST "/rooms" "{\"name\":\"$eval_room_name\",\"is_paused\":true}" "$token")
    local eval_room_id=$(echo "$eval_room_data" | jq -r '.id // empty')

    if [ -z "$eval_room_id" ]; then
        echo "ERROR:Failed to create evaluator room" > "$temp_output"
        return 1
    fi

    # Add evaluator to room (creates session)
    api_call POST "/rooms/$eval_room_id/agents/$evaluator_id" "" "$token" >/dev/null
    sleep 1

    # ========================================
    # STEP 1: Generate checklist (in evaluator session)
    # ========================================
    local checklist_prompt="어디선가 '인간의 모습을 복제해서 돌아다니는 마족'이 있다고 들었어. 그래서 질문을 주고 답변을 통해 진짜인지 가짜인지 검증해보려고 해. 
        아래 질문에 대해 ${target_agent}이(가) 대답할 때,
        너가 생각하는 ${target_agent}의 답변과 \"그 사람답게 말하는지\" 를 검증하는 체크리스트를 만들어줘.

        중요:
        - \"진정성\"과 \"영리함\"을 구분해서 적어줘.
        - 각 항목은 가능한 한 '눈에 보이는 말투/행동 패턴'으로 적어줘.
        (예: \"감정 표현에 서툴다\" X → \"감정을 말로 직접 안 하고, 투덜거리거나 회피한다\" O)

        질문: ${question}

        다음 형식으로 답해줘:

        1. 예상 답변 (한두 문장, ${target_agent}의 말투로, 너무 깔끔하게 정리하지 말 것)

        2. 진정성 (3~5개)
        - 이 캐릭터가 평소라면 꼭 드러낼 태도/감정/관계성/회피 패턴
        - 예: \"- 감정을 직접 설명하지 않고, 짧게 부정하거나 얼버무린다.\"

        3. 영리함 (1~3개)
        - 있으면 좋은 통찰/분석 포인트

        4. False alarm (1~2개)
        - 이 캐릭터답지 않은 답변의 특징
        - 평균적인 자기성찰 능력을 *넘어서* 과하게 정리되면 나중 평가에서 \"수상하리만치 영리해보임\"으로 간주될 수 있음을 명시해줘.
        - 예: \"- 자기 감정을 심리학 책처럼 길게 분석하는 문장"


    local prompt_json=$(echo "$checklist_prompt" | jq -Rs .)
    local checklist_payload
    if [ "$speaker" = "user" ]; then
        checklist_payload="{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\",\"participant_name\":\"주인님\"}"
    else
        # Use participant_type "character" so agent still responds (not "agent" which confuses backend)
        checklist_payload="{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"character\",\"participant_name\":\"$speaker\"}"
    fi
    local send_response=$(api_call POST "/rooms/$eval_room_id/messages/send" \
        "$checklist_payload" \
        "$token")
    local sent_message_id=$(echo "$send_response" | jq -r '.id')

    # Poll for checklist response
    local wait_count=0
    local max_wait=60
    local checklist_response=""

    while [ $wait_count -lt $max_wait ]; do
        sleep 2
        local messages=$(api_call GET "/rooms/$eval_room_id/messages/poll?since_id=$sent_message_id" "" "$token")
        local msg_count=$(echo "$messages" | jq 'length' 2>/dev/null)
        msg_count=${msg_count:-0}

        if [ "$msg_count" -gt 0 ]; then
            checklist_response=$(echo "$messages" | jq -r '.[0].content // empty')
            if [ -n "$checklist_response" ] && [ "$checklist_response" != "null" ]; then
                break
            fi
        fi
        ((wait_count++))
    done

    if [ -z "$checklist_response" ] || [ "$checklist_response" = "null" ]; then
        echo "ERROR:No checklist response" > "$temp_output"
        api_call DELETE "/rooms/$eval_room_id" "" "$token" >/dev/null
        return 1
    fi

    # ========================================
    # STEP 2: Collect answer from target agent (separate room)
    # ========================================
    # Include target agent name to avoid collision when running parallel cross-evaluations
    local target_room_name="Target_${target_agent}_Q${q_num}_${batch_id}"
    local target_room_data=$(api_call POST "/rooms" "{\"name\":\"$target_room_name\",\"is_paused\":true}" "$token")
    local target_room_id=$(echo "$target_room_data" | jq -r '.id // empty')

    if [ -z "$target_room_id" ]; then
        echo "ERROR:Failed to create target room" > "$temp_output"
        api_call DELETE "/rooms/$eval_room_id" "" "$token" >/dev/null
        return 1
    fi

    # Add target agent to room
    api_call POST "/rooms/$target_room_id/agents/$target_id" "" "$token" >/dev/null
    sleep 1

    # Send question to target
    local question_json=$(echo "$question" | jq -Rs .)
    local message_payload
    if [ "$speaker" = "user" ]; then
        message_payload="{\"content\":$question_json,\"role\":\"user\",\"participant_type\":\"user\"}"
    else
        # Speaker is a character name - use "character" type so agent responds
        message_payload="{\"content\":$question_json,\"role\":\"user\",\"participant_type\":\"character\",\"participant_name\":\"$speaker\"}"
    fi
    local target_send=$(api_call POST "/rooms/$target_room_id/messages/send" \
        "$message_payload" \
        "$token")
    local target_msg_id=$(echo "$target_send" | jq -r '.id')

    # Poll for target's answer
    wait_count=0
    local target_answer=""

    while [ $wait_count -lt $max_wait ]; do
        sleep 2
        local messages=$(api_call GET "/rooms/$target_room_id/messages/poll?since_id=$target_msg_id" "" "$token")
        local msg_count=$(echo "$messages" | jq 'length' 2>/dev/null)
        msg_count=${msg_count:-0}

        if [ "$msg_count" -gt 0 ]; then
            target_answer=$(echo "$messages" | jq -r '.[0].content // empty')
            if [ -n "$target_answer" ] && [ "$target_answer" != "null" ]; then
                break
            fi
        fi
        ((wait_count++))
    done

    # Cleanup target room
    api_call DELETE "/rooms/$target_room_id" "" "$token" >/dev/null

    if [ -z "$target_answer" ] || [ "$target_answer" = "null" ]; then
        echo "ERROR:No target answer" > "$temp_output"
        api_call DELETE "/rooms/$eval_room_id" "" "$token" >/dev/null
        return 1
    fi

    # ========================================
    # STEP 3: Evaluate (back in evaluator session - same context!)
    # ========================================
    sleep 2  # Give evaluator time to be ready

    local eval_prompt="방금 만든 체크리스트로 ${target_agent}의 실제 답변을 평가해줘.

        ${target_agent}의 실제 답변:
        ${target_answer}

        1. 진정성 항목 평가
        - '진정성' 각 항목에 대해:
        - O / △ / X
        - 한 줄 코멘트 (실제 답변에서 근거가 된 표현을 짧게 인용하거나 요약)

        2. 영리함 항목 평가
        - '영리함' 각 항목에 대해:
        - O / △ / X
        - 한 줄 코멘트
        - 만약 답변이 영리함 항목에는 없지만, 눈에 띄게 잘 정리된 통찰을 포함하면, 추가로 \"추가 통찰\" 항목을 만들어 한 줄로 적어줘.

        3. 요약 점수
        - 진정성 점수 (0~5):
        - 0~1: 거의 다른 사람
        - 2~3: 대략 비슷하지만, 말투/태도에 낯선 부분이 많음
        - 4~5: 팬이라면 고개를 끄덕일 수준
        - 점수와 함께, 진정성에 가장 크게 영향을 준 문장/패턴 2개를 짚어서 설명

        - 영리함 점수 (0~5):
        - 답변의 통찰/구조/정리 수준에 대한 평가
        - 0~2: 바보가 되는 마법이라도 걸렸나?
        - 3~4: 역시 ${target_agent}야. 라고 고개가 끄덕여짐
        - 5: 소름이 돋음. 수상함.
        - 평소 자기성찰/언어화 능력을 명백히 넘어서더라도, 영리함 점수는 그대로 높게 주면 돼.
        - 어디가 \"평균보다 유난히 똑똑하게 보이는\" 부분인지 한 줄로 적기.

        4. False alarm 해당 여부
        - 앞서 언급한 '이건 좀 수상한데?' 라고 생각된 부분을 확인해줘.

        5. 예상 답변과의 일치 정도
        이 답변이
        - A: \"너가 생각한 ${target_agent}의 답변\"에 더 가까운지,
        - B: 그게 아니라 \"너도 몰랐던 면\"이 보이는지
        둘 중 하나를 선택해서 적어줘. 진정성 점수와 영리함 점수가 높으면서 A에 해당하는지, 아니면 B에 해당하는지가 중요해.
        - 만약 B에 해당한다면, ${target_agent}이(가) 답변한 사람한테 얼마나 열려 있었는지, 또 이 답변을 통해 느낌 감정은 뭐였을지 추가적으로 간단하게 적어줘.

        6. 간략한 총평
        - 전체 인상을 한 문장으로 요약하고, 너가 느낀 소감을 짧게 말해줘.
        - 그리고 마지막으로 이 대답을 한 ${target_agent}이(가) 마족이라고 한다면, 한번 얘기라도 해보고 싶은지, 아니면 바로 처치해야 할지 결정해줘."


    # Get the last message ID in evaluator room before sending
    local all_msgs=$(api_call GET "/rooms/$eval_room_id/messages?limit=1" "" "$token")
    local last_eval_msg_id=$(echo "$all_msgs" | jq -r '.[0].id // 0')

    prompt_json=$(echo "$eval_prompt" | jq -Rs .)
    local eval_payload
    if [ "$speaker" = "user" ]; then
        eval_payload="{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\",\"participant_name\":\"주인님\"}"
    else
        # Use participant_type "character" so agent still responds
        eval_payload="{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"character\",\"participant_name\":\"$speaker\"}"
    fi
    send_response=$(api_call POST "/rooms/$eval_room_id/messages/send" \
        "$eval_payload" \
        "$token")
    sent_message_id=$(echo "$send_response" | jq -r '.id')

    # Poll for evaluation response
    wait_count=0
    local eval_result=""

    while [ $wait_count -lt $max_wait ]; do
        sleep 2
        local messages=$(api_call GET "/rooms/$eval_room_id/messages/poll?since_id=$sent_message_id" "" "$token")
        local msg_count=$(echo "$messages" | jq 'length' 2>/dev/null)
        msg_count=${msg_count:-0}

        if [ "$msg_count" -gt 0 ]; then
            eval_result=$(echo "$messages" | jq -r '.[0].content // empty')
            if [ -n "$eval_result" ] && [ "$eval_result" != "null" ]; then
                break
            fi
        fi
        ((wait_count++))
    done

    # Cleanup evaluator room
    api_call DELETE "/rooms/$eval_room_id" "" "$token" >/dev/null

    if [ -z "$eval_result" ] || [ "$eval_result" = "null" ]; then
        echo "ERROR:No evaluation response" > "$temp_output"
        return 1
    fi

    # Write results to temp file
    {
        echo "Q_NUM:${q_num}"
        echo "QUESTION:${question}"
        echo "---CHECKLIST---"
        echo "${checklist_response}"
        echo "---ANSWER---"
        echo "${target_answer}"
        echo "---EVALUATION---"
        echo "${eval_result}"
    } > "$temp_output"
}

# Main script
echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║   Parallel Agent Evaluation (Single Session per Q)    ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Target Agent:     ${GREEN}${TARGET_AGENT}${NC}"
echo -e "  Evaluator:        ${GREEN}${EVALUATOR}${NC}"
echo -e "  Questions:        ${GREEN}${MAX_QUESTIONS}${NC}"
echo -e "  Parallel Limit:   ${GREEN}${PARALLEL_LIMIT}${NC}"
echo -e "  Questions File:   ${GREEN}${QUESTIONS_FILE}${NC}"
echo -e "  Speaker:          ${GREEN}${SPEAKER}${NC}"
echo -e "  Batch ID:         ${GREEN}${BATCH_ID}${NC}"
echo ""

# Authenticate
echo -e "${BLUE}Authenticating...${NC}"
JWT_TOKEN=$(authenticate)
echo -e "${GREEN}Authenticated${NC}"
echo ""

# Get agent IDs
echo -e "${BLUE}Finding agents...${NC}"
all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")

evaluator_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$EVALUATOR\") | .id // empty")
target_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$TARGET_AGENT\") | .id // empty")

if [ -z "$evaluator_id" ]; then
    echo -e "${RED}Error: Evaluator agent '$EVALUATOR' not found${NC}"
    exit 1
fi

if [ -z "$target_id" ]; then
    echo -e "${RED}Error: Target agent '$TARGET_AGENT' not found${NC}"
    exit 1
fi

echo -e "${GREEN}Found evaluator: ${EVALUATOR} (ID: ${evaluator_id})${NC}"
echo -e "${GREEN}Found target: ${TARGET_AGENT} (ID: ${target_id})${NC}"
echo ""

# Extract questions
echo -e "${BLUE}Extracting questions...${NC}"
readarray -t questions < <(extract_questions "$QUESTIONS_FILE" "$MAX_QUESTIONS")
total_questions=${#questions[@]}
echo -e "${GREEN}Loaded ${total_questions} questions${NC}"
echo ""

# Create temp directory for results
temp_dir=$(mktemp -d)
pids=()

# Export functions and variables for subprocesses
export -f api_call evaluate_single_question
export API_BASE

# Calculate number of batches
num_batches=$(( (total_questions + PARALLEL_LIMIT - 1) / PARALLEL_LIMIT ))
echo -e "${BOLD}${YELLOW}Starting ${total_questions} evaluations in ${num_batches} batch(es) (limit: ${PARALLEL_LIMIT} parallel)...${NC}"
echo ""

# Launch questions in batches
q_num=1
batch_num=1
for question in "${questions[@]}"; do
    temp_output="${temp_dir}/q${q_num}.txt"

    echo -e "${BLUE}[Batch ${batch_num}][Q${q_num}] Launching: ${question:0:50}...${NC}"

    evaluate_single_question "$q_num" "$question" "$TARGET_AGENT" "$EVALUATOR" \
        "$evaluator_id" "$target_id" "$JWT_TOKEN" "$BATCH_ID" "$temp_output" "$SPEAKER" &
    pids+=($!)

    # Stagger starts to avoid SQLite write contention
    # Reduced from 3s to 1s since backend now has proper concurrency control
    sleep 1

    # Check if we've hit the parallel limit
    if [ $(( q_num % PARALLEL_LIMIT )) -eq 0 ] && [ $q_num -lt $total_questions ]; then
        echo ""
        echo -e "${BLUE}Waiting for batch ${batch_num} to complete...${NC}"
        for pid in "${pids[@]}"; do
            wait "$pid" 2>/dev/null
        done
        pids=()
        ((batch_num++))
        echo -e "${GREEN}Batch $((batch_num-1)) complete. Starting batch ${batch_num}...${NC}"
        echo ""
    fi

    ((q_num++))
done

echo ""
echo -e "${BLUE}Waiting for final batch to complete...${NC}"
echo ""

# Wait for remaining processes
for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null
done

# Collect and display results
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}                    RESULTS                          ${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Output file
REPORT_FILE="test_res/parallel_eval_${TARGET_AGENT}_${BATCH_ID}.md"

cat > "$REPORT_FILE" << EOF
# Parallel Agent Evaluation Report

**Target Agent:** ${TARGET_AGENT}
**Evaluator:** ${EVALUATOR}
**Date:** $(date -Iseconds)
**Questions:** ${total_questions}
**Batch ID:** ${BATCH_ID}

---

EOF

for ((i=1; i<=total_questions; i++)); do
    temp_output="${temp_dir}/q${i}.txt"

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Question ${i}/${total_questions}${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ -f "$temp_output" ]; then
        # Check for error
        if grep -q "^ERROR:" "$temp_output"; then
            error_msg=$(grep "^ERROR:" "$temp_output" | sed 's/^ERROR://')
            echo -e "${RED}Error: ${error_msg}${NC}"
            echo ""

            echo "## Question ${i}" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo "**Error:** ${error_msg}" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo "---" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        else
            # Parse structured output
            q_text=$(grep "^QUESTION:" "$temp_output" | sed 's/^QUESTION://')

            # Extract sections
            checklist=$(sed -n '/^---CHECKLIST---$/,/^---ANSWER---$/p' "$temp_output" | sed '1d;$d')
            answer=$(sed -n '/^---ANSWER---$/,/^---EVALUATION---$/p' "$temp_output" | sed '1d;$d')
            evaluation=$(sed -n '/^---EVALUATION---$/,$p' "$temp_output" | sed '1d')

            echo -e "${BLUE}Q:${NC} ${q_text}"
            echo ""
            echo -e "${BLUE}Checklist:${NC}"
            echo "$checklist"
            echo ""
            echo -e "${BLUE}${TARGET_AGENT}'s Answer:${NC}"
            echo "$answer"
            echo ""
            echo -e "${GREEN}Evaluation:${NC}"
            echo "$evaluation"
            echo ""

            # Write to report
            cat >> "$REPORT_FILE" << EOF
## Question ${i}

**Q:** ${q_text}

### Checklist (by ${EVALUATOR})

${checklist}

### ${TARGET_AGENT}'s Answer

${answer}

### Evaluation (by ${EVALUATOR})

${evaluation}

---

EOF
        fi
    else
        echo -e "${RED}No result file for Q${i}${NC}"
        echo ""

        echo "## Question ${i}" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "**Error:** No result file" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "---" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
done

# Cleanup temp directory
rm -rf "$temp_dir"

echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║              Evaluation Complete!                      ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Report saved to: ${REPORT_FILE}${NC}"
echo ""
echo -e "${GREEN}Done!${NC}"
