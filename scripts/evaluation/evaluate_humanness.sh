#!/bin/bash
# Evaluate which answer looks most human (blind comparison)
# Two-phase pipeline:
#   Phase 1: Collect answers from all agents for all questions (highly parallel)
#   Phase 2: Judge all collected answers (parallel)
#
# Usage: ./evaluate_humanness.sh --dataset workforce [--agents "jane,dr_chen"] [--limit N] [--parallel N]

set -euo pipefail

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
JUDGE_AGENT="judge"
POLL_INTERVAL=2
POLL_TIMEOUT=120

# Parsed options
DATASET="workforce"
AGENTS="jane"
PASSWORD=""
LIMIT=""
PARALLEL_QUESTIONS=5  # How many questions to process in parallel
QUIET=false
INCLUDE_HUMAN=true

# Runtime state
JWT_TOKEN=""
JUDGE_ID=""
RESULTS_FILE=""
BATCH_ID=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset|-d) DATASET="$2"; shift 2 ;;
        --agents|-a) AGENTS="$2"; shift 2 ;;
        --password|-p) PASSWORD="$2"; shift 2 ;;
        --limit|-l) LIMIT="$2"; shift 2 ;;
        --parallel|-P) PARALLEL_QUESTIONS="$2"; shift 2 ;;
        --no-human) INCLUDE_HUMAN=false; shift ;;
        --quiet|-q) QUIET=true; shift ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Two-phase humanness evaluation:"
            echo "  Phase 1: Collect all answers in parallel"
            echo "  Phase 2: Judge all answers in parallel"
            echo ""
            echo "Options:"
            echo "  --dataset, -d NAME     Dataset to evaluate (default: workforce)"
            echo "  --agents, -a LIST      Comma-separated agent names (default: jane)"
            echo "  --password, -p PWD     Authentication password"
            echo "  --limit, -l N          Evaluate only first N pairs"
            echo "  --parallel, -P N       Parallel questions (default: 5)"
            echo "  --no-human             Don't include human answer"
            echo "  --quiet, -q            Suppress progress output"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log() {
    if [ "$QUIET" != "true" ]; then
        echo -e "$@" >&2
    fi
}

# API call helper
api_call() {
    local method=$1
    local endpoint=$2
    local data=${3:-}
    local token=${4:-$JWT_TOKEN}

    local args=(-s -X "$method" "$API_BASE$endpoint")
    [ -n "$token" ] && args+=(-H "X-API-Key: $token")
    [ -n "$data" ] && args+=(-H "Content-Type: application/json" -d "$data")

    curl "${args[@]}" 2>/dev/null || true
}

authenticate() {
    if [ -z "$PASSWORD" ]; then
        [ -f "$PROJECT_ROOT/.env" ] && PASSWORD=$(grep '^CHITCHATS_PASSWORD=' "$PROJECT_ROOT/.env" | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    fi
    [ -z "$PASSWORD" ] && { echo -e "${YELLOW}Enter password:${NC}" >&2; read -s PASSWORD; echo "" >&2; }

    local response=$(api_call POST "/auth/login" "{\"password\":\"$PASSWORD\"}" "")
    local token=$(echo "$response" | jq -r '.api_key // empty')
    [ -z "$token" ] && { echo -e "${RED}Authentication failed${NC}" >&2; exit 1; }
    echo "$token"
}

# Get answer from an agent (standalone function for parallel execution)
# Writes result to file: $answers_dir/$agent_name.txt
collect_agent_answer() {
    local agent_id=$1
    local agent_name=$2
    local question=$3
    local context=$4
    local output_file=$5
    local room_suffix=$6
    local token=$7

    # Create room
    local room_name="collect_${agent_name}_${room_suffix}"
    local room_data=$(api_call POST "/rooms" "{\"name\":\"$room_name\",\"max_interactions\":10,\"is_paused\":true}" "$token")
    local room_id=$(echo "$room_data" | jq -r '.id // empty')
    [ -z "$room_id" ] && return 1

    # Add agent
    api_call POST "/rooms/$room_id/agents/$agent_id" "" "$token" >/dev/null
    sleep 0.3

    # Build prompt
    local prompt="You are participating in an interview. Please answer the following question naturally and authentically, as if you were a real person being interviewed.

INTERVIEW CONTEXT:
$context

INTERVIEWER'S QUESTION:
$question

Please respond naturally to this question. Answer as yourself - be genuine, share your real thoughts, and speak in your natural voice."

    local prompt_json=$(echo "$prompt" | jq -Rs .)

    # Send message
    local send_response=$(api_call POST "/rooms/$room_id/messages/send" \
        "{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\"}" "$token")
    local sent_id=$(echo "$send_response" | jq -r '.id // empty')

    if [ -z "$sent_id" ]; then
        api_call DELETE "/rooms/$room_id" "" "$token" >/dev/null 2>&1
        return 1
    fi

    # Poll for response
    local wait_count=0
    local max_wait=$((POLL_TIMEOUT / POLL_INTERVAL))

    while [ $wait_count -lt $max_wait ]; do
        sleep $POLL_INTERVAL
        local messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$sent_id" "" "$token")
        local response=$(echo "$messages" | jq -r '.[0].content // empty' 2>/dev/null)

        if [ -n "$response" ] && [ "$response" != "null" ]; then
            echo "$response" > "$output_file"
            break
        fi
        wait_count=$((wait_count + 1))
    done

    # Cleanup
    api_call DELETE "/rooms/$room_id" "" "$token" >/dev/null 2>&1
}

# Judge a single question's answers
# Reads question/context from files in q_dir
# Writes result to judgment.json
judge_answers() {
    local idx=$1
    local q_dir=$2
    local sources_file=$3
    local output_file=$4
    local judge_id=$5
    local token=$6
    local batch_id=$7

    # Read question and context from files (safer than passing as args)
    local question=$(cat "${q_dir}/question.txt")
    local context=$(cat "${q_dir}/context.txt")

    # Shuffle sources for blind comparison
    local shuffled_sources=$(shuf "$sources_file")
    local labels=("A" "B" "C" "D" "E")
    local label_idx=0
    local label_mapping_json="{"
    local answers_section=""
    local first_label=true

    while IFS= read -r source; do
        [ -z "$source" ] && continue
        local label="${labels[$label_idx]}"
        local answer=$(cat "${q_dir}/${source}.txt" 2>/dev/null || echo "")

        [ "$first_label" = "true" ] && first_label=false || label_mapping_json+=","
        label_mapping_json+="\"$label\":\"$source\""

        answers_section+="RESPONSE $label:
$answer

"
        label_idx=$((label_idx + 1))
    done <<< "$shuffled_sources"
    label_mapping_json+="}"

    # Create Judge room
    local judge_room_name="judge_${idx}_${batch_id}"
    local judge_room_data=$(api_call POST "/rooms" "{\"name\":\"$judge_room_name\",\"max_interactions\":10,\"is_paused\":true}" "$token")
    local judge_room_id=$(echo "$judge_room_data" | jq -r '.id // empty')
    [ -z "$judge_room_id" ] && { echo "{\"error\":\"Failed to create judge room\"}" > "$output_file"; return 1; }

    api_call POST "/rooms/$judge_room_id/agents/$judge_id" "" "$token" >/dev/null
    sleep 0.3

    local judge_prompt="You are evaluating multiple interview responses to determine which sounds most authentically human.

INTERVIEW CONTEXT:
$context

QUESTION ASKED:
$question

Here are the responses from different sources (presented in random order for blind comparison):

${answers_section}
Evaluate each response for how authentically human it sounds. Consider:
1. Natural language patterns and conversational flow
2. Personal touches, specific details, and genuine emotion
3. Imperfections that make it feel real (hesitation, tangents, incomplete thoughts)
4. Authentic voice and personality
5. Realistic perspective and lived experience

Respond with EXACTLY this format:
RANKING: [Labels from most human to least human, e.g., 'B, A, C']
MOST_HUMAN: [Single letter of most human response]
REASONING: [Your explanation in 2-3 sentences]"

    local prompt_json=$(echo "$judge_prompt" | jq -Rs .)
    local send_response=$(api_call POST "/rooms/$judge_room_id/messages/send" \
        "{\"content\":$prompt_json,\"role\":\"user\",\"participant_type\":\"user\"}" "$token")
    local sent_id=$(echo "$send_response" | jq -r '.id // empty')

    if [ -z "$sent_id" ]; then
        api_call DELETE "/rooms/$judge_room_id" "" "$token" >/dev/null 2>&1
        echo "{\"error\":\"Failed to send to judge\"}" > "$output_file"
        return 1
    fi

    # Poll for judge response
    local wait_count=0
    local max_wait=$((POLL_TIMEOUT / POLL_INTERVAL))
    local judge_response=""

    while [ $wait_count -lt $max_wait ]; do
        sleep $POLL_INTERVAL
        local messages=$(api_call GET "/rooms/$judge_room_id/messages/poll?since_id=$sent_id" "" "$token")
        judge_response=$(echo "$messages" | jq -r '.[0].content // empty' 2>/dev/null)

        if [ -n "$judge_response" ] && [ "$judge_response" != "null" ]; then
            break
        fi
        wait_count=$((wait_count + 1))
    done

    api_call DELETE "/rooms/$judge_room_id" "" "$token" >/dev/null 2>&1

    if [ -z "$judge_response" ] || [ "$judge_response" = "null" ]; then
        echo "{\"error\":\"Judge timeout\"}" > "$output_file"
        return 1
    fi

    # Parse judgment
    local most_human_label=$(echo "$judge_response" | sed -n 's/.*MOST_HUMAN:[[:space:]]*\([A-E]\).*/\1/p' | head -1 || true)
    local ranking=$(echo "$judge_response" | sed -n 's/.*RANKING:[[:space:]]*\(.*\)/\1/p' | head -1 || true)
    local reasoning=$(echo "$judge_response" | sed -n 's/.*REASONING:[[:space:]]*//p' | head -1 || true)
    [ -z "$reasoning" ] && reasoning="$judge_response"

    local most_human_source="unknown"
    [ -n "$most_human_label" ] && most_human_source=$(echo "$label_mapping_json" | jq -r ".\"$most_human_label\" // \"unknown\"")

    # Write result
    echo "{\"label_mapping\":$label_mapping_json,\"most_human_label\":\"$most_human_label\",\"most_human_source\":\"$most_human_source\",\"ranking\":\"$ranking\",\"reasoning\":$(echo "$reasoning" | jq -Rs .)}" > "$output_file"
}

# Export functions for subshells
export -f api_call collect_agent_answer judge_answers
export API_BASE POLL_INTERVAL POLL_TIMEOUT

main() {
    cd "$PROJECT_ROOT"
    BATCH_ID=$(date +%Y%m%d_%H%M%S)

    log "${BOLD}${BLUE}============================================================${NC}"
    log "${BOLD}${BLUE}       Humanness Evaluation (Two-Phase Pipeline)            ${NC}"
    log "${BOLD}${BLUE}============================================================${NC}"
    log ""
    log "${BLUE}Configuration:${NC}"
    log "  Dataset:           ${GREEN}${DATASET}${NC}"
    log "  Agents:            ${GREEN}${AGENTS}${NC}"
    log "  Parallel questions:${GREEN}${PARALLEL_QUESTIONS}${NC}"
    log "  Include Human:     ${GREEN}${INCLUDE_HUMAN}${NC}"
    log ""

    # Load pairs file
    local pairs_file="results/parsed/${DATASET}_pairs.json"
    [ ! -f "$pairs_file" ] && { log "${RED}Error: $pairs_file not found${NC}"; exit 1; }

    mkdir -p results/evaluations
    RESULTS_FILE="results/evaluations/humanness_${DATASET}_${BATCH_ID}.json"

    # Authenticate
    log "${BLUE}Authenticating...${NC}"
    JWT_TOKEN=$(authenticate)
    export JWT_TOKEN
    log "${GREEN}Authenticated${NC}"

    # Get agents
    log "${BLUE}Finding agents...${NC}"
    local all_agents=$(api_call GET "/agents" "" "$JWT_TOKEN")

    JUDGE_ID=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$JUDGE_AGENT\") | .id // empty")
    [ -z "$JUDGE_ID" ] && { log "${RED}Error: Judge agent not found${NC}"; exit 1; }
    log "${GREEN}Found Judge (ID: $JUDGE_ID)${NC}"

    local agent_names=()
    local agent_ids=()
    IFS=',' read -ra agent_list <<< "$AGENTS"
    for name in "${agent_list[@]}"; do
        name=$(echo "$name" | xargs)
        local id=$(echo "$all_agents" | jq -r ".[] | select(.name==\"$name\") | .id // empty")
        [ -z "$id" ] && { log "${RED}Error: Agent '$name' not found${NC}"; exit 1; }
        agent_names+=("$name")
        agent_ids+=("$id")
        log "${GREEN}Found: $name (ID: $id)${NC}"
    done
    log ""

    # Determine how many pairs to process
    local total_pairs=$(jq '.total_pairs' "$pairs_file")
    local limit_pairs=${LIMIT:-$total_pairs}
    [ "$limit_pairs" -gt "$total_pairs" ] && limit_pairs=$total_pairs

    log "${BLUE}Processing $limit_pairs questions...${NC}"
    log ""

    # Create temp directory
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    # ============================================================
    # PHASE 1: Collect all answers in parallel
    # ============================================================
    log "${BOLD}${YELLOW}PHASE 1: Collecting answers (${#agent_names[@]} agents × $limit_pairs questions)...${NC}"
    local phase1_start=$(date +%s)

    local collection_pids=()

    for ((idx=0; idx<limit_pairs; idx++)); do
        local q_dir="${temp_dir}/q_${idx}"
        mkdir -p "$q_dir"

        # Extract question data
        local context=$(jq -r ".pairs[$idx].context" "$pairs_file")
        local human_answer=$(jq -r ".pairs[$idx].current_answer" "$pairs_file")
        local question=$(echo "$context" | grep -oP '(?<=Q: ).*' | tail -1 || true)
        [ -z "$question" ] && question="Please share your thoughts on what we've been discussing."

        # Save question data for phase 2 (use printf for multiline safety)
        printf '%s\n' "$question" > "${q_dir}/question.txt"
        printf '%s\n' "$context" > "${q_dir}/context.txt"

        # Save human answer if enabled
        if [ "$INCLUDE_HUMAN" = "true" ]; then
            printf '%s\n' "$human_answer" > "${q_dir}/human.txt"
        fi

        # Launch parallel agent queries for this question
        for i in "${!agent_names[@]}"; do
            local agent_name="${agent_names[$i]}"
            local agent_id="${agent_ids[$i]}"
            local output_file="${q_dir}/${agent_name}.txt"

            (
                collect_agent_answer "$agent_id" "$agent_name" "$question" "$context" "$output_file" "${idx}_${BATCH_ID}" "$JWT_TOKEN"
            ) &
            collection_pids+=($!)
        done

        # Throttle: wait if we have too many parallel processes
        if [ ${#collection_pids[@]} -ge $((PARALLEL_QUESTIONS * ${#agent_names[@]})) ]; then
            log "  ${DIM}Waiting for batch (${#collection_pids[@]} processes)...${NC}"
            for pid in "${collection_pids[@]}"; do
                wait "$pid" 2>/dev/null || true
            done
            collection_pids=()
        fi
    done

    # Wait for remaining collection processes
    log "  ${DIM}Waiting for final collection batch...${NC}"
    for pid in "${collection_pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    local phase1_end=$(date +%s)
    local phase1_time=$((phase1_end - phase1_start))
    log "${GREEN}Phase 1 complete: ${phase1_time}s${NC}"
    log ""

    # ============================================================
    # PHASE 2: Judge all answers in parallel
    # ============================================================
    log "${BOLD}${YELLOW}PHASE 2: Judging answers...${NC}"
    local phase2_start=$(date +%s)

    local judge_pids=()
    local active_judges=0

    for ((idx=0; idx<limit_pairs; idx++)); do
        local q_dir="${temp_dir}/q_${idx}"
        local sources_file="${q_dir}/sources.txt"
        local judge_output="${q_dir}/judgment.json"

        # Build sources file from collected answers
        > "$sources_file"
        for agent_name in "${agent_names[@]}"; do
            [ -f "${q_dir}/${agent_name}.txt" ] && [ -s "${q_dir}/${agent_name}.txt" ] && echo "$agent_name" >> "$sources_file"
        done
        [ "$INCLUDE_HUMAN" = "true" ] && [ -f "${q_dir}/human.txt" ] && echo "human" >> "$sources_file"

        local source_count=$(wc -l < "$sources_file")
        if [ "$source_count" -lt 2 ]; then
            echo "{\"error\":\"Not enough answers\"}" > "$judge_output"
            continue
        fi

        (
            judge_answers "$idx" "$q_dir" "$sources_file" "$judge_output" "$JUDGE_ID" "$JWT_TOKEN" "$BATCH_ID"
        ) &
        judge_pids+=($!)
        active_judges=$((active_judges + 1))

        # Throttle judges
        if [ $active_judges -ge $PARALLEL_QUESTIONS ]; then
            log "  ${DIM}Waiting for judge batch...${NC}"
            for pid in "${judge_pids[@]}"; do
                wait "$pid" 2>/dev/null || true
            done
            judge_pids=()
            active_judges=0
        fi
    done

    # Wait for remaining judges
    for pid in "${judge_pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    local phase2_end=$(date +%s)
    local phase2_time=$((phase2_end - phase2_start))
    log "${GREEN}Phase 2 complete: ${phase2_time}s${NC}"
    log ""

    # ============================================================
    # Compile results
    # ============================================================
    log "${BLUE}Compiling results...${NC}"

    local human_wins=0
    local agent_wins=0
    local total_complete=0
    local failures=0

    local start_time=$(date -Iseconds)
    echo "{\"metadata\":{\"dataset\":\"$DATASET\",\"agents\":\"$AGENTS\",\"include_human\":$INCLUDE_HUMAN,\"batch_id\":\"$BATCH_ID\",\"total_evaluations\":0,\"human_wins\":0,\"agent_wins\":0,\"human_detection_rate\":0,\"failures\":0,\"start_time\":\"$start_time\",\"end_time\":null,\"phase1_seconds\":$phase1_time,\"phase2_seconds\":$phase2_time},\"evaluations\":[],\"failures\":[]}" > "$RESULTS_FILE"

    for ((idx=0; idx<limit_pairs; idx++)); do
        local q_dir="${temp_dir}/q_${idx}"
        local eval_id=$(jq -r ".pairs[$idx].eval_id" "$pairs_file")
        local judge_output="${q_dir}/judgment.json"

        if [ ! -f "$judge_output" ]; then
            failures=$((failures + 1))
            jq ".failures += [{\"eval_id\":\"$eval_id\",\"error\":\"No judgment file\"}]" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
            continue
        fi

        local error=$(jq -r '.error // empty' "$judge_output" 2>/dev/null)
        if [ -n "$error" ]; then
            failures=$((failures + 1))
            jq ".failures += [{\"eval_id\":\"$eval_id\",\"error\":\"$error\"}]" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
            continue
        fi

        local most_human_source=$(jq -r '.most_human_source' "$judge_output")
        local human_won="N/A"

        if [ "$INCLUDE_HUMAN" = "true" ]; then
            if [ "$most_human_source" = "human" ]; then
                human_won="true"
                human_wins=$((human_wins + 1))
            else
                human_won="false"
                agent_wins=$((agent_wins + 1))
            fi
        fi

        total_complete=$((total_complete + 1))

        # Build answers JSON
        local answers_json="{"
        local first=true
        local sources_file="${q_dir}/sources.txt"
        while IFS= read -r source; do
            [ -z "$source" ] && continue
            local ans=$(cat "${q_dir}/${source}.txt" 2>/dev/null | jq -Rs .)
            [ "$first" = "true" ] && first=false || answers_json+=","
            answers_json+="\"$source\":$ans"
        done < "$sources_file"
        answers_json+="}"

        local question=$(cat "${q_dir}/question.txt")
        local judgment=$(cat "$judge_output")

        local eval_entry=$(jq -n \
            --arg eval_id "$eval_id" \
            --arg question "$question" \
            --argjson answers "$answers_json" \
            --argjson judgment "$judgment" \
            --arg human_won "$human_won" \
            --arg timestamp "$(date -Iseconds)" \
            '{evaluation_id:$eval_id,question:$question,answers:$answers,judgment:$judgment,human_won:$human_won,timestamp:$timestamp}')

        jq ".evaluations += [$eval_entry]" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
    done

    # Update final metadata
    local detection_rate=0
    [ $total_complete -gt 0 ] && [ "$INCLUDE_HUMAN" = "true" ] && detection_rate=$(echo "scale=3; $human_wins / $total_complete" | bc)

    local end_time=$(date -Iseconds)
    jq ".metadata.total_evaluations=$total_complete|.metadata.human_wins=$human_wins|.metadata.agent_wins=$agent_wins|.metadata.human_detection_rate=$detection_rate|.metadata.failures=$failures|.metadata.end_time=\"$end_time\"" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"

    # Summary
    log ""
    log "${BOLD}${GREEN}============================================================${NC}"
    log "${BOLD}${GREEN}              Evaluation Complete!                          ${NC}"
    log "${BOLD}${GREEN}============================================================${NC}"
    log ""
    log "${BLUE}Total: $total_complete evaluations${NC}"
    [ "$INCLUDE_HUMAN" = "true" ] && {
        log "${GREEN}Human wins:  $human_wins${NC}"
        log "${YELLOW}Agent wins:  $agent_wins${NC}"
        [ $total_complete -gt 0 ] && log "${CYAN}Detection rate: $(echo "scale=1; $human_wins * 100 / $total_complete" | bc)%${NC}"
    }
    log "${RED}Failures:    $failures${NC}"
    log ""
    log "${BLUE}Phase 1 (collection): ${phase1_time}s${NC}"
    log "${BLUE}Phase 2 (judging):    ${phase2_time}s${NC}"
    log "${BLUE}Results: $RESULTS_FILE${NC}"
}

main "$@"
echo "$RESULTS_FILE"
