#!/bin/bash
# Main script to evaluate agent authenticity using checklist-based approach
# Usage: ./evaluate_authenticity.sh --target-agent "프리렌" --evaluator "페른" --questions 5

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
QUESTIONS_FILE=""
PASSWORD=""
JWT_TOKEN=""
KEEP_INTERMEDIATE=false

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
        --password)
            PASSWORD="$2"
            shift 2
            ;;
        --token)
            JWT_TOKEN="$2"
            shift 2
            ;;
        --keep-intermediate)
            KEEP_INTERMEDIATE=true
            shift
            ;;
        --help)
            echo "Agent Authenticity Evaluation System"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "This script evaluates agent authenticity through a 3-step process:"
            echo "  1. Generate checklists (evaluator predicts expected responses)"
            echo "  2. Collect answers (target agent responds to questions)"
            echo "  3. Evaluate (evaluator checks answers against checklists)"
            echo ""
            echo "Options:"
            echo "  --target-agent NAME    Agent to evaluate (default: 프리렌)"
            echo "  --evaluator NAME       Agent performing evaluation (default: 페른)"
            echo "  --questions N          Number of questions (default: 5)"
            echo "  --questions-file FILE  Path to questions file"
            echo "  --password PASS        Authentication password"
            echo "  --token TOKEN          JWT token (skip auth)"
            echo "  --keep-intermediate    Keep intermediate YAML files"
            echo ""
            echo "Example:"
            echo "  $0 --target-agent \"프리렌\" --evaluator \"페른\" --questions 3"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
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
    echo "Please create a questions file at this location or specify --questions-file"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Generate batch ID
BATCH_ID=$(date +%s)

# Create test_res directory if it doesn't exist
mkdir -p test_res

# Output filenames (all in test_res/)
CHECKLIST_FILE="test_res/checklists_${TARGET_AGENT}_${BATCH_ID}.yaml"
ANSWERS_FILE="test_res/answers_${TARGET_AGENT}_${BATCH_ID}.yaml"
EVALUATION_FILE="test_res/evaluation_${TARGET_AGENT}_${BATCH_ID}.yaml"
REPORT_FILE="test_res/report_${TARGET_AGENT}_${BATCH_ID}.md"

echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║     Agent Authenticity Evaluation System              ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Target Agent:     ${GREEN}${TARGET_AGENT}${NC}"
echo -e "  Evaluator:        ${GREEN}${EVALUATOR}${NC}"
echo -e "  Questions:        ${GREEN}${MAX_QUESTIONS}${NC}"
echo -e "  Questions File:   ${GREEN}${QUESTIONS_FILE}${NC}"
echo -e "  Batch ID:         ${GREEN}${BATCH_ID}${NC}"
echo ""

# Load from .env if available
if [ -f ".env" ] && [ -z "$JWT_TOKEN" ]; then
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [ -z "$PASSWORD" ]; then
        PASSWORD=$(grep '^CHITCHATS_PASSWORD=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
    fi
fi

# Prepare arguments for subscripts
COMMON_ARGS="--questions $MAX_QUESTIONS --questions-file \"$QUESTIONS_FILE\""
if [ -n "$PASSWORD" ]; then
    COMMON_ARGS="$COMMON_ARGS --password \"$PASSWORD\""
fi
if [ -n "$JWT_TOKEN" ]; then
    COMMON_ARGS="$COMMON_ARGS --token \"$JWT_TOKEN\""
fi

# Create persistent evaluation room and session
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}Setup: Creating persistent evaluation room${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Source the API functions from generate_checklists.sh
API_BASE="${BACKEND_URL:-http://localhost:8000}"

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

# Authenticate
echo -e "${BLUE}Authenticating...${NC}"
JWT_TOKEN=$(authenticate)
echo -e "${GREEN}Authenticated${NC}"
echo ""

# Get evaluator agent ID
echo -e "${BLUE}Finding evaluator agent: ${EVALUATOR}${NC}"
all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")
evaluator_id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$EVALUATOR\") | .id // empty")

if [ -z "$evaluator_id" ]; then
    echo -e "${RED}Error: Evaluator agent '$EVALUATOR' not found${NC}"
    exit 1
fi
echo -e "${GREEN}Found evaluator: ${EVALUATOR} (ID: ${evaluator_id})${NC}"
echo ""

# Create persistent evaluation room
EVAL_ROOM_NAME="Evaluation_${TARGET_AGENT}_${BATCH_ID}"
echo -e "${BLUE}Creating persistent evaluation room: ${EVAL_ROOM_NAME}${NC}"
room_data=$(api_call POST "/rooms" "{\"name\":\"$EVAL_ROOM_NAME\",\"is_paused\":true}" "$JWT_TOKEN")
EVAL_ROOM_ID=$(echo "$room_data" | jq -r '.id // empty')

if [ -z "$EVAL_ROOM_ID" ]; then
    echo -e "${RED}Error: Failed to create evaluation room${NC}"
    exit 1
fi
echo -e "${GREEN}Created room (ID: ${EVAL_ROOM_ID})${NC}"
echo ""

# Add evaluator to room (this creates the persistent session)
echo -e "${BLUE}Adding ${EVALUATOR} to room (creating session)...${NC}"
add_response=$(api_call POST "/rooms/$EVAL_ROOM_ID/agents/$evaluator_id" "" "$JWT_TOKEN")
echo -e "${GREEN}✓ Session created for ${EVALUATOR}${NC}"
echo ""
sleep 2

# Step 1: Generate Checklists
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${YELLOW}STEP 1: Generate Checklists (${EVALUATOR})${NC}"
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

eval "$SCRIPT_DIR/generate_checklists.sh \
    --target-agent \"$TARGET_AGENT\" \
    --evaluator \"$EVALUATOR\" \
    --output \"$CHECKLIST_FILE\" \
    --room-id \"$EVAL_ROOM_ID\" \
    $COMMON_ARGS"

if [ $? -ne 0 ] || [ ! -f "$CHECKLIST_FILE" ]; then
    echo -e "${RED}Error: Checklist generation failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Checklists generated: ${CHECKLIST_FILE}${NC}"
echo ""
sleep 2

# Step 2: Collect Answers
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${YELLOW}STEP 2: Collect Answers (${TARGET_AGENT})${NC}"
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

eval "$SCRIPT_DIR/collect_answers.sh \
    --target-agent \"$TARGET_AGENT\" \
    --output \"$ANSWERS_FILE\" \
    $COMMON_ARGS"

if [ $? -ne 0 ] || [ ! -f "$ANSWERS_FILE" ]; then
    echo -e "${RED}Error: Answer collection failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Answers collected: ${ANSWERS_FILE}${NC}"
echo ""
sleep 2

# Step 3: Evaluate Responses
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${YELLOW}STEP 3: Evaluate Responses (${EVALUATOR})${NC}"
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Build auth args for step 3
STEP3_ARGS="--evaluator \"$EVALUATOR\" --checklist \"$CHECKLIST_FILE\" --answers \"$ANSWERS_FILE\" --output \"$EVALUATION_FILE\" --room-id \"$EVAL_ROOM_ID\""
if [ -n "$PASSWORD" ]; then
    STEP3_ARGS="$STEP3_ARGS --password \"$PASSWORD\""
fi
if [ -n "$JWT_TOKEN" ]; then
    STEP3_ARGS="$STEP3_ARGS --token \"$JWT_TOKEN\""
fi

eval "$SCRIPT_DIR/evaluate_responses.sh $STEP3_ARGS"

if [ $? -ne 0 ] || [ ! -f "$EVALUATION_FILE" ]; then
    echo -e "${RED}Error: Evaluation failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Evaluation completed: ${EVALUATION_FILE}${NC}"
echo ""

# Generate readable report
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}Generating Report${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cat > "$REPORT_FILE" << EOF
# Agent Authenticity Evaluation Report

**Target Agent:** ${TARGET_AGENT}
**Evaluator:** ${EVALUATOR}
**Date:** $(date -Iseconds)
**Questions:** ${MAX_QUESTIONS}
**Batch ID:** ${BATCH_ID}

---

## Summary

This evaluation assesses ${TARGET_AGENT}'s authenticity by comparing responses against
checklists created by ${EVALUATOR}.

**Evaluation Scale:**
- **O** (완전히 충족): Fully meets the checklist criteria
- **△** (부분적으로 충족): Partially meets the criteria
- **X** (충족하지 못함): Does not meet the criteria

---

## Detailed Results

EOF

# Extract and format evaluation results
awk '
    /question_id:/ {
        in_question = 1
        qid = $2
        print "\n### Question " qid "\n"
    }
    in_question && /question:/ {
        getline
        while ($0 ~ /^      /) {
            print $0
            getline
        }
        print ""
    }
    in_question && /evaluation:/ {
        print "**Evaluation:**\n"
        getline
        while ($0 ~ /^      /) {
            print $0
            getline
        }
        print "\n---\n"
    }
' "$EVALUATION_FILE" >> "$REPORT_FILE"

cat >> "$REPORT_FILE" << EOF

---

## Files Generated

- Checklists: \`${CHECKLIST_FILE}\`
- Answers: \`${ANSWERS_FILE}\`
- Evaluation: \`${EVALUATION_FILE}\`
- Report: \`${REPORT_FILE}\`

---

*Generated by ChitChats Agent Evaluation System*
EOF

echo -e "${GREEN}✓ Report generated: ${REPORT_FILE}${NC}"
echo ""

# Cleanup evaluation room
echo -e "${BLUE}Cleaning up evaluation room...${NC}"
api_call DELETE "/rooms/$EVAL_ROOM_ID" "" "$JWT_TOKEN" >/dev/null
echo -e "${GREEN}✓ Room cleaned up${NC}"
echo ""

# Summary
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║              Evaluation Complete!                      ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Generated Files:${NC}"
echo -e "  📋 Checklists:  ${CHECKLIST_FILE}"
echo -e "  💬 Answers:     ${ANSWERS_FILE}"
echo -e "  ✅ Evaluation:  ${EVALUATION_FILE}"
echo -e "  📄 Report:      ${REPORT_FILE}"
echo ""

# Cleanup intermediate files if requested
if [ "$KEEP_INTERMEDIATE" = false ]; then
    echo -e "${YELLOW}Note: Intermediate YAML files will be kept for reference.${NC}"
    echo -e "${YELLOW}Use --keep-intermediate flag if you want to preserve all files.${NC}"
    echo ""
fi

echo -e "${BLUE}View the report:${NC}"
echo -e "  cat ${REPORT_FILE}"
echo ""
echo -e "${GREEN}Done!${NC}"
