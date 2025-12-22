#!/bin/bash
# Evaluate Jane's question-generation quality against original interviewer questions
# Judge provides comparative evaluations in a blind comparison
# Runs evaluations in parallel batches for efficiency
#
# Usage: ./evaluate_questions.sh --dataset creatives [--password pwd] [--limit N] [--parallel N]

set -euo pipefail
set -o noglob  # Prevent glob expansion (important for responses with asterisks)

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
API_BASE="${BACKEND_URL:-http://localhost:8001}"
JANE_AGENT="jane"
JUDGE_AGENT="judge"
POLL_INTERVAL=2
POLL_TIMEOUT=120
CHECKPOINT_INTERVAL=10

# Parsed options
DATASET="creatives"
PASSWORD=""
LIMIT=""
PARALLEL_LIMIT=10
QUIET=false

# Runtime state
JWT_TOKEN=""
JANE_ID=""
JUDGE_ID=""
RESULTS_FILE=""
BATCH_ID=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset|-d)
            DATASET="$2"
            shift 2
            ;;
        --password|-p)
            PASSWORD="$2"
            shift 2
            ;;
        --limit|-l)
            LIMIT="$2"
            shift 2
            ;;
        --parallel|-P)
            PARALLEL_LIMIT="$2"
            shift 2
            ;;
        --quiet|-q)
            QUIET=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --dataset, -d NAME     Dataset to evaluate (default: creatives)"
            echo "  --password, -p PWD     Authentication password"
            echo "  --limit, -l N          Evaluate only first N pairs"
            echo "  --parallel, -P N       Max parallel evaluations (default: 10)"
            echo "  --quiet, -q            Suppress progress output"
            echo "  --help, -h             Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
log() {
    if [ "$QUIET" != "true" ]; then
        echo -e "$@" >&2
    fi
}

# API call helper with retry logic
api_call() {
    local method=$1
    local endpoint=$2
    local data=${3:-}
    local token=${4:-$JWT_TOKEN}
    local max_retries=3
    local retry_delay=1

    local args=(-s -X "$method" "$API_BASE$endpoint")

    if [ -n "$token" ]; then
        args+=(-H "X-API-Key: $token")
    fi

    if [ -n "$data" ]; then
        args+=(-H "Content-Type: application/json" -d "$data")
    fi

    for ((attempt=1; attempt<=max_retries; attempt++)); do
        local response=$(curl "${args[@]}" 2>/dev/null)

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

# Authenticate and get JWT token
authenticate() {
    if [ -z "$PASSWORD" ]; then
        if [ -f "$PROJECT_ROOT/.env" ]; then
            PASSWORD=$(grep '^CHITCHATS_PASSWORD=' "$PROJECT_ROOT/.env" | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
        fi
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

# Evaluate a single pair (runs in its own subprocess)
# Reads pair data from JSON file to avoid bash quoting issues with special characters
evaluate_single_pair() {
    local idx=$1
    local pairs_file=$2
    local jane_id=$3
    local judge_id=$4
    local token=$5
    local batch_id=$6
    local temp_output=$7

    # Read pair data from JSON file (avoids bash quoting issues)
    local pair=$(jq ".pairs[$idx]" "$pairs_file")
    local eval_id=$(echo "$pair" | jq -r '.eval_id')
    local context=$(echo "$pair" | jq -r '.context')
    local current_answer=$(echo "$pair" | jq -r '.current_answer')
    local original_question=$(echo "$pair" | jq -r '.original_question')

    local start_time=$(date +%s%3N)

    # Create Jane room
    local jane_room_name="jane_eval_${idx}_${batch_id}"
    local jane_room_data=$(api_call POST "/rooms" "{\"name\":\"$jane_room_name\",\"max_interactions\":10,\"is_paused\":true}" "$token")
    local jane_room_id=$(echo "$jane_room_data" | jq -r '.id // empty')

    if [ -z "$jane_room_id" ]; then
        echo "{\"error\": \"Failed to create Jane room\"}" > "$temp_output"
        return 1
    fi

    # Add Jane to room
    api_call POST "/rooms/$jane_room_id/agents/$jane_id" "" "$token" >/dev/null
    sleep 0.5

    # Build prompt for Jane
    local jane_prompt="You are helping evaluate interview question quality. Given the following interview context and the user's most recent answer, generate ONE thoughtful follow-up question that would naturally continue this interview.

INTERVIEW CONTEXT:
$context

CURRENT ANSWER FROM INTERVIEWEE:
$current_answer

Generate exactly ONE follow-up question. Output ONLY the question itself, nothing else - no explanations, no preamble, just the question."

    local prompt_json=$(echo "$jane_prompt" | jq -Rs .)

    # Send to Jane
    local send_response=$(api_call POST "/rooms/$jane_room_id/messages/send" \
        "{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\"}" \
        "$token")
    local sent_id=$(echo "$send_response" | jq -r '.id // empty')

    if [ -z "$sent_id" ]; then
        api_call DELETE "/rooms/$jane_room_id" "" "$token" >/dev/null 2>&1
        echo "{\"error\": \"Failed to send to Jane\"}" > "$temp_output"
        return 1
    fi

    # Poll for Jane's response
    local wait_count=0
    local max_wait=$((POLL_TIMEOUT / POLL_INTERVAL))
    local jane_response=""
    local jane_thinking=""

    while [ $wait_count -lt $max_wait ]; do
        sleep $POLL_INTERVAL

        local messages=$(api_call GET "/rooms/$jane_room_id/messages/poll?since_id=$sent_id" "" "$token")
        local msg_count=$(echo "$messages" | jq 'length' 2>/dev/null || echo "0")

        if [ "$msg_count" -gt 0 ]; then
            jane_response=$(echo "$messages" | jq -r '.[0].content // empty')
            jane_thinking=$(echo "$messages" | jq -r '.[0].thinking // empty')

            if [ -n "$jane_response" ] && [ "$jane_response" != "null" ]; then
                break
            fi
        fi

        wait_count=$((wait_count + 1))
    done

    local gen_end_time=$(date +%s%3N)
    local generation_time=$((gen_end_time - start_time))

    # Cleanup Jane room
    api_call DELETE "/rooms/$jane_room_id" "" "$token" >/dev/null 2>&1

    if [ -z "$jane_response" ] || [ "$jane_response" = "null" ]; then
        echo "{\"error\": \"Jane timeout\"}" > "$temp_output"
        return 1
    fi

    # Create Judge room
    local judge_room_name="judge_eval_${idx}_${batch_id}"
    local judge_room_data=$(api_call POST "/rooms" "{\"name\":\"$judge_room_name\",\"max_interactions\":10,\"is_paused\":true}" "$token")
    local judge_room_id=$(echo "$judge_room_data" | jq -r '.id // empty')

    if [ -z "$judge_room_id" ]; then
        echo "{\"error\": \"Failed to create Judge room\"}" > "$temp_output"
        return 1
    fi

    # Add Judge to room
    api_call POST "/rooms/$judge_room_id/agents/$judge_id" "" "$token" >/dev/null
    sleep 0.5

    # Randomize order for blind comparison
    local order=$((RANDOM % 2))
    local question_a question_b
    if [ $order -eq 0 ]; then
        question_a="$original_question"
        question_b="$jane_response"
    else
        question_a="$jane_response"
        question_b="$original_question"
    fi

    # Build prompt for Judge
    local judge_prompt="You are evaluating two follow-up questions for an interview. Given the context and the interviewee's most recent answer, judge which question would better continue the interview.

INTERVIEW CONTEXT:
$context

INTERVIEWEE'S ANSWER:
$current_answer

QUESTION A:
$question_a

QUESTION B:
$question_b

Evaluate based on:
1. Relevance to the answer given
2. Depth and thoughtfulness
3. Ability to elicit rich responses
4. Natural conversation flow and smooth transition for proceeding the interview program

Respond with EXACTLY this format:
WINNER: [A or B or TIE]
REASONING: [Your explanation in 2-3 sentences]"

    prompt_json=$(echo "$judge_prompt" | jq -Rs .)

    # Send to Judge
    local eval_start=$(date +%s%3N)
    send_response=$(api_call POST "/rooms/$judge_room_id/messages/send" \
        "{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\"}" \
        "$token")
    sent_id=$(echo "$send_response" | jq -r '.id // empty')

    if [ -z "$sent_id" ]; then
        api_call DELETE "/rooms/$judge_room_id" "" "$token" >/dev/null 2>&1
        echo "{\"error\": \"Failed to send to Judge\"}" > "$temp_output"
        return 1
    fi

    # Poll for Judge's response
    wait_count=0
    local judge_response=""
    local judge_thinking=""

    while [ $wait_count -lt $max_wait ]; do
        sleep $POLL_INTERVAL

        local messages=$(api_call GET "/rooms/$judge_room_id/messages/poll?since_id=$sent_id" "" "$token")
        local msg_count=$(echo "$messages" | jq 'length' 2>/dev/null || echo "0")

        if [ "$msg_count" -gt 0 ]; then
            judge_response=$(echo "$messages" | jq -r '.[0].content // empty')
            judge_thinking=$(echo "$messages" | jq -r '.[0].thinking // empty')

            if [ -n "$judge_response" ] && [ "$judge_response" != "null" ]; then
                break
            fi
        fi

        wait_count=$((wait_count + 1))
    done

    local eval_end=$(date +%s%3N)
    local evaluation_time=$((eval_end - eval_start))

    # Cleanup Judge room
    api_call DELETE "/rooms/$judge_room_id" "" "$token" >/dev/null 2>&1

    if [ -z "$judge_response" ] || [ "$judge_response" = "null" ]; then
        echo "{\"error\": \"Judge timeout\"}" > "$temp_output"
        return 1
    fi

    # Parse judgment
    local winner=""
    if echo "$judge_response" | grep -qi "WINNER:.*A"; then
        winner="A"
    elif echo "$judge_response" | grep -qi "WINNER:.*B"; then
        winner="B"
    elif echo "$judge_response" | grep -qi "WINNER:.*TIE"; then
        winner="TIE"
    else
        winner="UNKNOWN"
    fi

    local reasoning=$(echo "$judge_response" | sed -n 's/.*REASONING:\s*//p' | head -1)
    if [ -z "$reasoning" ]; then
        reasoning="$judge_response"
    fi

    # Convert winner to judgment (0=original, 1=jane, 2=tie)
    local judgment
    if [ $order -eq 0 ]; then
        case "$winner" in
            A) judgment=0 ;;
            B) judgment=1 ;;
            TIE) judgment=2 ;;
            *) judgment=-1 ;;
        esac
    else
        case "$winner" in
            A) judgment=1 ;;
            B) judgment=0 ;;
            TIE) judgment=2 ;;
            *) judgment=-1 ;;
        esac
    fi

    # Write result to temp file as JSON
    local timestamp=$(date -Iseconds)
    jq -n \
        --arg eval_id "$eval_id" \
        --arg context "$context" \
        --arg current_answer "$current_answer" \
        --arg original_question "$original_question" \
        --arg jane_question "$jane_response" \
        --arg jane_thinking "$jane_thinking" \
        --argjson judgment "$judgment" \
        --arg reasoning "$reasoning" \
        --arg judge_thinking "$judge_thinking" \
        --argjson generation_time "$generation_time" \
        --argjson evaluation_time "$evaluation_time" \
        --arg timestamp "$timestamp" \
        '{
            evaluation_id: $eval_id,
            context: $context,
            current_answer: $current_answer,
            original_question: $original_question,
            jane_question: $jane_question,
            jane_thinking: $jane_thinking,
            judgment: $judgment,
            reasoning: $reasoning,
            judge_thinking: $judge_thinking,
            generation_time_ms: $generation_time,
            evaluation_time_ms: $evaluation_time,
            timestamp: $timestamp
        }' > "$temp_output"
}

# Signal handler
handle_sigint() {
    log "\n${YELLOW}Interrupted. Cleaning up...${NC}"
    # Kill all child processes
    pkill -P $$ 2>/dev/null || true
    exit 130
}

trap handle_sigint SIGINT SIGTERM

# Main execution
main() {
    cd "$PROJECT_ROOT"

    BATCH_ID=$(date +%Y%m%d_%H%M%S)

    log "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    log "${BOLD}${BLUE}║      Question Evaluation Pipeline (Parallel)           ║${NC}"
    log "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    log ""
    log "${BLUE}Configuration:${NC}"
    log "  Dataset:        ${GREEN}${DATASET}${NC}"
    log "  Parallel Limit: ${GREEN}${PARALLEL_LIMIT}${NC}"
    log "  Batch ID:       ${GREEN}${BATCH_ID}${NC}"
    log ""

    # Load parsed pairs
    local pairs_file="results/parsed/${DATASET}_pairs.json"
    if [ ! -f "$pairs_file" ]; then
        log "${RED}Error: Parsed pairs file not found: $pairs_file${NC}"
        log "${YELLOW}Run: ./scripts/evaluation/parse_transcripts.sh --dataset $DATASET${NC}"
        exit 1
    fi

    # Setup output file
    RESULTS_FILE="results/evaluations/${DATASET}_${BATCH_ID}.json"

    # Authenticate
    log "${BLUE}Authenticating...${NC}"
    JWT_TOKEN=$(authenticate)
    log "${GREEN}Authenticated${NC}"
    log ""

    # Get agent IDs
    log "${BLUE}Finding agents...${NC}"
    local all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")

    JANE_ID=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$JANE_AGENT\") | .id // empty")
    JUDGE_ID=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$JUDGE_AGENT\") | .id // empty")

    if [ -z "$JANE_ID" ]; then
        log "${RED}Error: Jane agent not found${NC}"
        exit 1
    fi
    if [ -z "$JUDGE_ID" ]; then
        log "${RED}Error: Judge agent not found${NC}"
        exit 1
    fi

    log "${GREEN}Found Jane (ID: $JANE_ID)${NC}"
    log "${GREEN}Found Judge (ID: $JUDGE_ID)${NC}"
    log ""

    # Load pairs
    local total_pairs=$(jq '.total_pairs' "$pairs_file")
    local limit_pairs=$total_pairs
    if [ -n "$LIMIT" ]; then
        limit_pairs=$LIMIT
    fi

    log "${BLUE}Processing $limit_pairs pairs (of $total_pairs total)...${NC}"
    log ""

    # Create temp directory for results
    local temp_dir=$(mktemp -d)
    local pids=()

    # Export functions and variables for subprocesses
    export -f api_call evaluate_single_pair
    export API_BASE POLL_INTERVAL POLL_TIMEOUT

    # Initialize counters
    local jane_wins=0
    local original_wins=0
    local ties=0
    local failures=0

    # Initialize results file
    local start_time=$(date -Iseconds)
    cat > "$RESULTS_FILE" << EOF
{
  "metadata": {
    "dataset": "$DATASET",
    "batch_id": "$BATCH_ID",
    "total_evaluations": 0,
    "jane_wins": 0,
    "original_wins": 0,
    "ties": 0,
    "failures": 0,
    "win_rate": 0,
    "start_time": "$start_time",
    "end_time": null
  },
  "evaluations": [],
  "failures": []
}
EOF

    # Calculate batches
    local num_batches=$(( (limit_pairs + PARALLEL_LIMIT - 1) / PARALLEL_LIMIT ))
    log "${BOLD}${YELLOW}Starting $limit_pairs evaluations in $num_batches batch(es) (limit: $PARALLEL_LIMIT parallel)...${NC}"
    log ""

    # Process in batches
    local batch_num=1
    local idx=0

    while [ $idx -lt $limit_pairs ]; do
        pids=()
        local batch_start=$idx
        local batch_end=$((idx + PARALLEL_LIMIT))
        if [ $batch_end -gt $limit_pairs ]; then
            batch_end=$limit_pairs
        fi

        log "${BLUE}[Batch $batch_num] Launching evaluations $((batch_start+1))-$batch_end...${NC}"

        # Launch batch
        for ((i=batch_start; i<batch_end; i++)); do
            local temp_output="${temp_dir}/eval_${i}.json"

            evaluate_single_pair "$i" "$pairs_file" "$JANE_ID" "$JUDGE_ID" "$JWT_TOKEN" "$BATCH_ID" "$temp_output" &
            pids+=($!)

            # Small stagger to avoid API overload
            sleep 0.3
        done

        # Wait for batch to complete
        log "${DIM}Waiting for batch $batch_num to complete...${NC}"
        for pid in "${pids[@]}"; do
            wait "$pid" 2>/dev/null || true
        done

        # Collect batch results
        for ((i=batch_start; i<batch_end; i++)); do
            local temp_output="${temp_dir}/eval_${i}.json"
            local eval_id=$(jq -r ".pairs[$i].eval_id" "$pairs_file")

            if [ -f "$temp_output" ]; then
                local error=$(jq -r '.error // empty' "$temp_output" 2>/dev/null)

                if [ -n "$error" ] && [ "$error" != "null" ]; then
                    log "  ${RED}[$((i+1))] $eval_id: FAILED ($error)${NC}"
                    failures=$((failures + 1))

                    # Record failure
                    local failure_entry=$(jq -n \
                        --arg eval_id "$eval_id" \
                        --arg error "$error" \
                        '{eval_id: $eval_id, error: $error}')
                    jq ".failures += [$failure_entry]" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
                else
                    local judgment=$(jq -r '.judgment' "$temp_output")

                    case "$judgment" in
                        0) original_wins=$((original_wins + 1)); log "  ${YELLOW}[$((i+1))] $eval_id: Original wins${NC}" ;;
                        1) jane_wins=$((jane_wins + 1)); log "  ${GREEN}[$((i+1))] $eval_id: Jane wins${NC}" ;;
                        2) ties=$((ties + 1)); log "  ${BLUE}[$((i+1))] $eval_id: Tie${NC}" ;;
                        *) failures=$((failures + 1)); log "  ${RED}[$((i+1))] $eval_id: Unknown judgment${NC}" ;;
                    esac

                    # Append evaluation to results
                    local eval_entry=$(cat "$temp_output")
                    jq ".evaluations += [$eval_entry]" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
                fi
            else
                log "  ${RED}[$((i+1))] $eval_id: No result file${NC}"
                failures=$((failures + 1))
            fi
        done

        # Update metadata
        local total_complete=$((jane_wins + original_wins + ties))
        local win_rate=0
        if [ $total_complete -gt 0 ]; then
            win_rate=$(echo "scale=3; $jane_wins / $total_complete" | bc)
        fi

        jq ".metadata.total_evaluations = $total_complete |
            .metadata.jane_wins = $jane_wins |
            .metadata.original_wins = $original_wins |
            .metadata.ties = $ties |
            .metadata.failures = $failures |
            .metadata.win_rate = $win_rate" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"

        log "${GREEN}Batch $batch_num complete. Running totals: Jane=$jane_wins, Original=$original_wins, Ties=$ties${NC}"
        log ""

        idx=$batch_end
        ((batch_num++))
    done

    # Cleanup temp directory
    rm -rf "$temp_dir"

    # Finalize metadata
    local end_time=$(date -Iseconds)
    jq ".metadata.end_time = \"$end_time\"" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"

    # Print summary
    log ""
    log "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    log "${BOLD}${GREEN}║              Evaluation Complete!                      ║${NC}"
    log "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    log ""
    log "${BLUE}Total: $((jane_wins + original_wins + ties)) evaluations${NC}"
    log "${GREEN}Jane wins:     $jane_wins${NC}"
    log "${YELLOW}Original wins: $original_wins${NC}"
    log "${BLUE}Ties:          $ties${NC}"
    log "${RED}Failures:      $failures${NC}"

    if [ $((jane_wins + original_wins + ties)) -gt 0 ]; then
        local final_rate=$(echo "scale=1; $jane_wins * 100 / ($jane_wins + $original_wins + $ties)" | bc)
        log "${CYAN}Win rate: ${final_rate}%${NC}"
    fi

    log ""
    log "${BLUE}Results saved to: $RESULTS_FILE${NC}"
}

# Run main and output results file path
main "$@"

# Output path for scripting (only thing that goes to stdout)
echo "$RESULTS_FILE"
