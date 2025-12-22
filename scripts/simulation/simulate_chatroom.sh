#!/bin/bash
# ChitChats Chatroom Simulation Script
# Usage: ./simulate_chatroom.sh [options]
#
# This script simulates multi-agent chatroom conversations via curl API calls.
# It authenticates, creates a room, adds agents, sends a scenario, polls for
# messages, and saves the transcript to chatroom_n.txt.
#
# Options:
#   -p, --password PASSWORD      API password for authentication
#   -t, --token TOKEN            JWT token (reads from .env if available)
#   -s, --scenario TEXT          Scenario/situation to send to agents
#   -a, --agents AGENT1,AGENT2   Comma-separated list of agent names
#   -r, --room-name NAME         Room name (default: Simulation_<timestamp>)
#   -m, --max-interactions N     Maximum interaction rounds (default: 10)
#   -o, --output FILE            Output file (default: chatroom_<n>.txt)
#   -u, --url URL                Backend URL (default: http://localhost:8001)
#   --no-system-prompt           Skip system prompt optimization for multi-round talks
#   --no-thinking                Exclude agent thinking/reasoning from transcript
#   --save-config                Save system prompt and tool config to separate file
#   -v, --variants N             Run N parallel simulations with same scenario (default: 1)
#   -h, --help                   Show this help message

set -e  # Exit on error

# Load JWT token from .env if it exists
if [ -f ".env" ]; then
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
fi

# Default configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"
PASSWORD="${CHITCHATS_PASSWORD:-}"
JWT_TOKEN="${JWT_TOKEN:-}"
SCENARIO=""
AGENTS=""
ROOM_NAME="Simulation_$(date +%s)"
MAX_INTERACTIONS=20
OUTPUT_FILE=""
POLL_INTERVAL=2  # seconds between polls
MAX_POLL_ATTEMPTS=600  # 20 minutes max (600 * 2s = 1200s)
MAX_NO_NEW_MESSAGE=60  # Stop after 60 polls with no new messages (2 minutes of silence)
NO_SYSTEM_PROMPT=false
NO_THINKING=false
SAVE_CONFIG=false
VARIANTS=1

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--password)
            PASSWORD="$2"
            shift 2
            ;;
        -t|--token)
            JWT_TOKEN="$2"
            shift 2
            ;;
        -s|--scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -a|--agents)
            AGENTS="$2"
            shift 2
            ;;
        -r|--room-name)
            ROOM_NAME="$2"
            shift 2
            ;;
        -m|--max-interactions)
            MAX_INTERACTIONS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -u|--url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --no-system-prompt)
            NO_SYSTEM_PROMPT=true
            shift 1
            ;;
        --no-thinking)
            NO_THINKING=true
            shift 1
            ;;
        --save-config)
            SAVE_CONFIG=true
            shift 1
            ;;
        -v|--variants)
            VARIANTS="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,22p' "$0" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$PASSWORD" ] && [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}Error: Password or JWT token is required${NC}"
    echo "Use -p/--password, -t/--token, set CHITCHATS_PASSWORD environment variable,"
    echo "or add JWT_TOKEN to .env file"
    exit 1
fi

if [ -z "$SCENARIO" ]; then
    echo -e "${RED}Error: Scenario is required${NC}"
    echo "Use -s/--scenario to specify the scenario text"
    exit 1
fi

if [ -z "$AGENTS" ]; then
    echo -e "${RED}Error: Agents are required${NC}"
    echo "Use -a/--agents to specify comma-separated agent names (e.g., 'alice,bob,charlie')"
    exit 1
fi

# Validate variants
if ! [[ "$VARIANTS" =~ ^[1-9][0-9]*$ ]]; then
    echo -e "${RED}Error: Variants must be a positive integer${NC}"
    exit 1
fi

# Auto-generate output filename if not specified
if [ -z "$OUTPUT_FILE" ]; then
    # Find next available chatroom_n.txt filename
    n=1
    if [ "$VARIANTS" -eq 1 ]; then
        while [ -f "chatroom_${n}.txt" ]; do
            n=$((n + 1))
        done
        OUTPUT_FILE="chatroom_${n}.txt"
    else
        # For variants, find base number where no variants exist
        while [ -f "chatroom_${n}_v1.txt" ]; do
            n=$((n + 1))
        done
        OUTPUT_FILE="chatroom_${n}.txt"
    fi
fi
OUTPUT_BASE="${OUTPUT_FILE%.txt}"

echo -e "${BLUE}=== ChitChats Chatroom Simulation ===${NC}"
echo "Backend: $BACKEND_URL"
echo "Room: $ROOM_NAME"
echo "Agents: $AGENTS"
echo "Max interactions: $MAX_INTERACTIONS"
if [ "$VARIANTS" -eq 1 ]; then
    echo "Output: $OUTPUT_FILE"
else
    echo "Variants: $VARIANTS (parallel runs)"
    echo "Output: ${OUTPUT_BASE}_v1.txt ... ${OUTPUT_BASE}_v${VARIANTS}.txt"
fi
if [ "$NO_SYSTEM_PROMPT" = false ]; then
    echo "System prompt optimization: Enabled"
else
    echo "System prompt optimization: Disabled"
fi
if [ "$NO_THINKING" = true ]; then
    echo "Include thinking: No (excluded from transcript)"
else
    echo "Include thinking: Yes"
fi
if [ "$SAVE_CONFIG" = true ]; then
    echo "Save configuration: Enabled (${OUTPUT_BASE}_config.txt)"
fi
echo ""

# Function to make API calls with error handling
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_header=$4

    local args=(-s -X "$method" "$BACKEND_URL$endpoint")

    if [ -n "$auth_header" ]; then
        args+=(-H "X-API-Key: $auth_header")
    fi

    if [ -n "$data" ]; then
        args+=(-H "Content-Type: application/json" -d "$data")
    fi

    curl "${args[@]}"
}

# Function to save system prompt and configuration
save_config() {
    local config_file=$1
    local agent_names=$2

    echo "================================================================================" > "$config_file"
    echo "ChitChats System Configuration" >> "$config_file"
    echo "================================================================================" >> "$config_file"
    echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$config_file"
    echo "Room: $ROOM_NAME" >> "$config_file"
    echo "Agents: $agent_names" >> "$config_file"
    echo "" >> "$config_file"

    # Read system prompt
    echo "================================================================================" >> "$config_file"
    echo "SYSTEM PROMPT (backend/config/system_prompt.txt)" >> "$config_file"
    echo "================================================================================" >> "$config_file"
    if [ -f "backend/config/system_prompt.txt" ]; then
        cat "backend/config/system_prompt.txt" >> "$config_file"
    else
        echo "[File not found]" >> "$config_file"
    fi
    echo "" >> "$config_file"

    # Read tools configuration
    echo "================================================================================" >> "$config_file"
    echo "TOOLS CONFIGURATION (backend/config/tools/tools.yaml)" >> "$config_file"
    echo "================================================================================" >> "$config_file"
    if [ -f "backend/config/tools/tools.yaml" ]; then
        cat "backend/config/tools/tools.yaml" >> "$config_file"
    else
        echo "[File not found]" >> "$config_file"
    fi
    echo "" >> "$config_file"

    # Read guidelines configuration
    echo "================================================================================" >> "$config_file"
    echo "GUIDELINES CONFIGURATION (backend/config/tools/guidelines.yaml)" >> "$config_file"
    echo "================================================================================" >> "$config_file"
    if [ -f "backend/config/tools/guidelines.yaml" ]; then
        cat "backend/config/tools/guidelines.yaml" >> "$config_file"
    else
        echo "[File not found]" >> "$config_file"
    fi
    echo "" >> "$config_file"

    # Read agent configurations
    echo "================================================================================" >> "$config_file"
    echo "AGENT CONFIGURATIONS" >> "$config_file"
    echo "================================================================================" >> "$config_file"
    IFS=',' read -ra AGENT_ARRAY <<< "$agent_names"
    for agent_name in "${AGENT_ARRAY[@]}"; do
        agent_name=$(echo "$agent_name" | xargs)
        echo "" >> "$config_file"
        echo "--- Agent: $agent_name ---" >> "$config_file"
        echo "" >> "$config_file"

        local agent_dir="agents/$agent_name"
        if [ -d "$agent_dir" ]; then
            for md_file in "$agent_dir"/*.md; do
                if [ -f "$md_file" ]; then
                    local filename=$(basename "$md_file")
                    echo "## $filename:" >> "$config_file"
                    cat "$md_file" >> "$config_file"
                    echo "" >> "$config_file"
                fi
            done
        else
            echo "[Agent directory not found: $agent_dir]" >> "$config_file"
        fi
    done

    echo "================================================================================" >> "$config_file"
    echo "End of Configuration" >> "$config_file"
    echo "================================================================================" >> "$config_file"
}

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    echo "Install with: sudo apt-get install jq (Debian/Ubuntu) or brew install jq (macOS)"
    exit 1
fi

# Function to run a single simulation variant
# Arguments: variant_num, variant_room_name, variant_output_file
run_simulation() {
    local variant_num=$1
    local v_room_name=$2
    local v_output_file=$3
    local prefix="[v${variant_num}]"

    # Step 2: Create room
    echo -e "${YELLOW}${prefix} Creating room '$v_room_name'...${NC}"
    local room_response=$(api_call POST "/rooms" "{\"name\":\"$v_room_name\",\"max_interactions\":$MAX_INTERACTIONS}" "$TOKEN")
    local room_id=$(echo "$room_response" | jq -r '.id // empty')
    if [ -z "$room_id" ]; then
        echo -e "${RED}${prefix} Error: Failed to create room${NC}"
        echo "$room_response" | jq '.' 2>/dev/null || echo "$room_response"
        return 1
    fi
    echo -e "${GREEN}${prefix} Room created (ID: $room_id)${NC}"

    # Step 4: Add agents to room
    echo -e "${YELLOW}${prefix} Adding agents to room...${NC}"
    IFS=',' read -ra agent_array <<< "$AGENTS"

    for agent_name in "${agent_array[@]}"; do
        agent_name=$(echo "$agent_name" | xargs)
        local agent_id=$(echo "$ALL_AGENTS" | jq -r ".[] | select(.name==\"$agent_name\") | .id // empty")

        if [ -z "$agent_id" ]; then
            echo -e "${RED}${prefix} Error: Agent '$agent_name' not found${NC}"
            return 1
        fi

        local add_response=$(api_call POST "/rooms/$room_id/agents/$agent_id" "" "$TOKEN")
        if echo "$add_response" | jq -e '.id' >/dev/null 2>&1; then
            echo -e "${GREEN}${prefix}   ✓ Added $agent_name${NC}"
        else
            echo -e "${RED}${prefix} Error: Failed to add agent '$agent_name'${NC}"
            return 1
        fi
    done

    # Step 5: Send scenario as situation_builder
    echo -e "${YELLOW}${prefix} Sending scenario...${NC}"
    local scenario_json=$(echo "$SCENARIO" | jq -Rs .)
    local send_response=$(api_call POST "/rooms/$room_id/messages/send" \
        "{\"content\":$scenario_json,\"role\":\"user\",\"participant_type\":\"situation_builder\"}" \
        "$TOKEN")

    if ! echo "$send_response" | jq -e '.id' >/dev/null 2>&1; then
        echo -e "${RED}${prefix} Error: Failed to send scenario${NC}"
        return 1
    fi
    echo -e "${GREEN}${prefix} Scenario sent${NC}"

    # Step 6: Poll for messages and save transcript
    echo -e "${YELLOW}${prefix} Waiting for agents to respond...${NC}"
    local last_message_id=0
    local poll_count=0
    local no_new_message_count=0

    # Initialize output file with header
    cat > "$v_output_file" << EOF
================================================================================
ChitChats Simulation Transcript
================================================================================
Room: $v_room_name (ID: $room_id)
Variant: $variant_num
Agents: $AGENTS
Scenario: $SCENARIO
Max Interactions: $MAX_INTERACTIONS
System Prompt Optimization: $(if [ "$NO_SYSTEM_PROMPT" = false ]; then echo "Enabled"; else echo "Disabled"; fi)
Include Thinking: $(if [ "$NO_THINKING" = false ]; then echo "Yes"; else echo "No"; fi)
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
================================================================================

EOF

    echo -e "${BLUE}${prefix} Polling for messages...${NC}"

    while [ $poll_count -lt $MAX_POLL_ATTEMPTS ]; do
        local messages=$(api_call GET "/rooms/$room_id/messages/poll?since_id=$last_message_id" "" "$TOKEN")
        local new_message_count=$(echo "$messages" | jq 'length')

        if [ "$new_message_count" -gt 0 ]; then
            no_new_message_count=0

            local jq_filter
            if [ "$NO_THINKING" = true ]; then
                jq_filter='.[] |
                    "--- " +
                    (if .participant_type == "situation_builder" then "Situation Builder"
                     elif .participant_type == "user" then "User"
                     elif .agent_name then .agent_name
                     else "Unknown" end) +
                    " (" + .timestamp + ") ---\n" +
                    .content + "\n"'
            else
                jq_filter='.[] |
                    "--- " +
                    (if .participant_type == "situation_builder" then "Situation Builder"
                     elif .participant_type == "user" then "User"
                     elif .agent_name then .agent_name
                     else "Unknown" end) +
                    " (" + .timestamp + ") ---\n" +
                    (if .thinking and .thinking != "" and .thinking != null then
                        "[Thinking]\n" + .thinking + "\n[/Thinking]\n\n"
                     else "" end) +
                    .content + "\n"'
            fi
            echo "$messages" | jq -r "$jq_filter" >> "$v_output_file"

            last_message_id=$(echo "$messages" | jq -r '.[-1].id')
            echo -e "${GREEN}${prefix}   Received $new_message_count message(s) (poll: $poll_count)${NC}"
        else
            no_new_message_count=$((no_new_message_count + 1))

            if [ $no_new_message_count -ge $MAX_NO_NEW_MESSAGE ]; then
                echo -e "${BLUE}${prefix}   Conversation complete (no messages for $((MAX_NO_NEW_MESSAGE * POLL_INTERVAL))s)${NC}"
                break
            fi
        fi

        sleep $POLL_INTERVAL
        poll_count=$((poll_count + 1))
    done

    # Add footer to transcript
    cat >> "$v_output_file" << EOF

================================================================================
Simulation Complete
Variant: $variant_num
Total Polls: $poll_count
End Time: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
================================================================================
EOF

    echo -e "${GREEN}${prefix} Complete - saved to $v_output_file${NC}"
    return 0
}

# Step 1: Authenticate (or use existing token)
if [ -n "$JWT_TOKEN" ]; then
    echo -e "${YELLOW}[1/4] Using existing JWT token...${NC}"
    TOKEN="$JWT_TOKEN"
    echo -e "${GREEN}✓ Token loaded${NC}"
else
    echo -e "${YELLOW}[1/4] Authenticating with password...${NC}"
    AUTH_RESPONSE=$(api_call POST "/auth/login" "{\"password\":\"$PASSWORD\"}" "")

    TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.api_key // empty')
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}Error: Authentication failed${NC}"
        echo "$AUTH_RESPONSE" | jq '.' 2>/dev/null || echo "$AUTH_RESPONSE"
        exit 1
    fi
    echo -e "${GREEN}✓ Authenticated successfully${NC}"

    if [ -f ".env" ] && ! grep -q "^JWT_TOKEN=" .env; then
        echo ""
        echo -e "${BLUE}💡 Tip: Add this line to .env to skip authentication next time:${NC}"
        echo -e "${BLUE}JWT_TOKEN=$TOKEN${NC}"
    fi
fi

# Step 2: Get all available agents (do this once for all variants)
echo -e "${YELLOW}[2/4] Fetching available agents...${NC}"
ALL_AGENTS=$(api_call GET "/agents" "" "$TOKEN")

# Validate agents exist before starting variants
IFS=',' read -ra AGENT_ARRAY <<< "$AGENTS"
for agent_name in "${AGENT_ARRAY[@]}"; do
    agent_name=$(echo "$agent_name" | xargs)
    AGENT_ID=$(echo "$ALL_AGENTS" | jq -r ".[] | select(.name==\"$agent_name\") | .id // empty")
    if [ -z "$AGENT_ID" ]; then
        echo -e "${RED}Error: Agent '$agent_name' not found${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ All agents validated${NC}"

# Save configuration if requested (do this once)
if [ "$SAVE_CONFIG" = true ]; then
    CONFIG_FILE="${OUTPUT_BASE}_config.txt"
    echo -e "${YELLOW}[3/4] Saving system configuration to $CONFIG_FILE...${NC}"
    save_config "$CONFIG_FILE" "$AGENTS"
    echo -e "${GREEN}✓ Configuration saved${NC}"
else
    echo -e "${YELLOW}[3/4] Skipping config save (not requested)${NC}"
fi

# Step 4: Run simulation(s)
echo -e "${YELLOW}[4/4] Starting simulation(s)...${NC}"
echo ""

if [ "$VARIANTS" -eq 1 ]; then
    # Single variant - run directly
    run_simulation 1 "$ROOM_NAME" "$OUTPUT_FILE"
    RESULT=$?
else
    # Multiple variants - run in parallel
    echo -e "${BLUE}Launching $VARIANTS parallel simulations...${NC}"
    PIDS=()

    for v in $(seq 1 $VARIANTS); do
        v_room="${ROOM_NAME}_v${v}"
        v_output="${OUTPUT_BASE}_v${v}.txt"

        run_simulation "$v" "$v_room" "$v_output" &
        PIDS+=($!)
        echo -e "${BLUE}  Started variant $v (PID: ${PIDS[-1]})${NC}"
    done

    echo ""
    echo -e "${BLUE}Waiting for all variants to complete...${NC}"

    # Wait for all background processes
    FAILED=0
    for i in "${!PIDS[@]}"; do
        wait "${PIDS[$i]}" || FAILED=$((FAILED + 1))
    done

    if [ $FAILED -gt 0 ]; then
        echo -e "${RED}Warning: $FAILED variant(s) failed${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=== Simulation Complete ===${NC}"
if [ "$VARIANTS" -eq 1 ]; then
    echo -e "Transcript saved to: ${BLUE}$OUTPUT_FILE${NC}"
else
    echo -e "Transcripts saved to: ${BLUE}${OUTPUT_BASE}_v1.txt ... ${OUTPUT_BASE}_v${VARIANTS}.txt${NC}"
fi
if [ "$SAVE_CONFIG" = true ]; then
    echo -e "Configuration saved to: ${BLUE}${OUTPUT_BASE}_config.txt${NC}"
fi
echo ""
