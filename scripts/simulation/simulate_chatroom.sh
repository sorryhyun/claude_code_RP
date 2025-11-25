#!/bin/bash
# Claude Code Role Play Chatroom Simulation Script
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
#   -u, --url URL                Backend URL (default: http://localhost:8000)
#   --no-system-prompt           Skip system prompt optimization for multi-round talks
#   --save-config                Save system prompt and tool config to separate file
#   -h, --help                   Show this help message

set -e  # Exit on error

# Load JWT token from .env if it exists
if [ -f ".env" ]; then
    JWT_TOKEN=$(grep '^JWT_TOKEN=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
fi

# Default configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
PASSWORD="${CCRP_PASSWORD:-}"
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
SAVE_CONFIG=false

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
        --save-config)
            SAVE_CONFIG=true
            shift 1
            ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# //'
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
    echo "Use -p/--password, -t/--token, set CCRP_PASSWORD environment variable,"
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

# Auto-generate output filename if not specified
if [ -z "$OUTPUT_FILE" ]; then
    # Find next available chatroom_n.txt filename
    n=1
    while [ -f "chatroom_${n}.txt" ]; do
        n=$((n + 1))
    done
    OUTPUT_FILE="chatroom_${n}.txt"
fi

echo -e "${BLUE}=== Claude Code Role Play Chatroom Simulation ===${NC}"
echo "Backend: $BACKEND_URL"
echo "Room: $ROOM_NAME"
echo "Agents: $AGENTS"
echo "Max interactions: $MAX_INTERACTIONS"
echo "Output: $OUTPUT_FILE"
if [ "$NO_SYSTEM_PROMPT" = false ]; then
    echo "System prompt optimization: Enabled"
else
    echo "System prompt optimization: Disabled"
fi
if [ "$SAVE_CONFIG" = true ]; then
    echo "Save configuration: Enabled (${OUTPUT_FILE%.txt}_config.txt)"
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
    echo "Claude Code Role Play System Configuration" >> "$config_file"
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

# Step 1: Authenticate (or use existing token)
if [ -n "$JWT_TOKEN" ]; then
    echo -e "${YELLOW}[1/6] Using existing JWT token...${NC}"
    TOKEN="$JWT_TOKEN"
    echo -e "${GREEN}✓ Token loaded${NC}"
else
    echo -e "${YELLOW}[1/6] Authenticating with password...${NC}"
    AUTH_RESPONSE=$(api_call POST "/auth/login" "{\"password\":\"$PASSWORD\"}" "")

    # Extract token
    TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.api_key // empty')
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}Error: Authentication failed${NC}"
        echo "$AUTH_RESPONSE" | jq '.' 2>/dev/null || echo "$AUTH_RESPONSE"
        exit 1
    fi
    echo -e "${GREEN}✓ Authenticated successfully${NC}"

    # Optionally save token to .env for future use
    if [ -f ".env" ] && ! grep -q "^JWT_TOKEN=" .env; then
        echo ""
        echo -e "${BLUE}💡 Tip: Add this line to .env to skip authentication next time:${NC}"
        echo -e "${BLUE}JWT_TOKEN=$TOKEN${NC}"
    fi
fi

# Step 2: Create room
echo -e "${YELLOW}[2/6] Creating room '$ROOM_NAME'...${NC}"
ROOM_RESPONSE=$(api_call POST "/rooms" "{\"name\":\"$ROOM_NAME\",\"max_interactions\":$MAX_INTERACTIONS}" "$TOKEN")
ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r '.id // empty')
if [ -z "$ROOM_ID" ]; then
    echo -e "${RED}Error: Failed to create room${NC}"
    echo "$ROOM_RESPONSE" | jq '.' 2>/dev/null || echo "$ROOM_RESPONSE"
    exit 1
fi
echo -e "${GREEN}✓ Room created (ID: $ROOM_ID)${NC}"

# Step 3: Get all available agents
echo -e "${YELLOW}[3/6] Fetching available agents...${NC}"
ALL_AGENTS=$(api_call GET "/agents" "" "$TOKEN")

# Step 4: Add agents to room
echo -e "${YELLOW}[4/6] Adding agents to room...${NC}"
IFS=',' read -ra AGENT_ARRAY <<< "$AGENTS"
AGENT_IDS=()

for agent_name in "${AGENT_ARRAY[@]}"; do
    # Trim whitespace
    agent_name=$(echo "$agent_name" | xargs)

    # Find agent ID by name
    AGENT_ID=$(echo "$ALL_AGENTS" | jq -r ".[] | select(.name==\"$agent_name\") | .id // empty")

    if [ -z "$AGENT_ID" ]; then
        echo -e "${RED}Error: Agent '$agent_name' not found${NC}"
        exit 1
    fi

    # Add agent to room
    ADD_RESPONSE=$(api_call POST "/rooms/$ROOM_ID/agents/$AGENT_ID" "" "$TOKEN")
    if echo "$ADD_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Added $agent_name (ID: $AGENT_ID)${NC}"
        AGENT_IDS+=("$AGENT_ID")
    else
        echo -e "${RED}Error: Failed to add agent '$agent_name'${NC}"
        echo "$ADD_RESPONSE" | jq '.' 2>/dev/null || echo "$ADD_RESPONSE"
        exit 1
    fi
done

# Save configuration if requested
if [ "$SAVE_CONFIG" = true ]; then
    CONFIG_FILE="${OUTPUT_FILE%.txt}_config.txt"
    echo -e "${YELLOW}Saving system configuration to $CONFIG_FILE...${NC}"
    save_config "$CONFIG_FILE" "$AGENTS"
    echo -e "${GREEN}✓ Configuration saved${NC}"
fi

# Step 5: Send scenario as situation_builder
echo -e "${YELLOW}[5/6] Sending scenario...${NC}"
# Escape JSON string properly
SCENARIO_JSON=$(echo "$SCENARIO" | jq -Rs .)
SEND_RESPONSE=$(api_call POST "/rooms/$ROOM_ID/messages/send" \
    "{\"content\":$SCENARIO_JSON,\"role\":\"user\",\"participant_type\":\"situation_builder\"}" \
    "$TOKEN")

if ! echo "$SEND_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
    echo -e "${RED}Error: Failed to send scenario${NC}"
    echo "$SEND_RESPONSE" | jq '.' 2>/dev/null || echo "$SEND_RESPONSE"
    exit 1
fi
echo -e "${GREEN}✓ Scenario sent${NC}"

# Step 6: Poll for messages and save transcript
echo -e "${YELLOW}[6/6] Waiting for agents to respond...${NC}"
LAST_MESSAGE_ID=0
POLL_COUNT=0
NO_NEW_MESSAGE_COUNT=0

# Initialize output file with header
cat > "$OUTPUT_FILE" << EOF
================================================================================
Claude Code Role Play Simulation Transcript
================================================================================
Room: $ROOM_NAME (ID: $ROOM_ID)
Agents: $AGENTS
Scenario: $SCENARIO
Max Interactions: $MAX_INTERACTIONS
System Prompt Optimization: $(if [ "$NO_SYSTEM_PROMPT" = false ]; then echo "Enabled"; else echo "Disabled"; fi)
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
================================================================================

EOF

echo -e "${BLUE}Polling for messages (this may take a while)...${NC}"

while [ $POLL_COUNT -lt $MAX_POLL_ATTEMPTS ]; do
    # Poll for new messages
    MESSAGES=$(api_call GET "/rooms/$ROOM_ID/messages/poll?since_id=$LAST_MESSAGE_ID" "" "$TOKEN")

    # Check if we got new messages
    NEW_MESSAGE_COUNT=$(echo "$MESSAGES" | jq 'length')

    if [ "$NEW_MESSAGE_COUNT" -gt 0 ]; then
        # Reset no-new-message counter
        NO_NEW_MESSAGE_COUNT=0

        # Process and append new messages to transcript (including thinking)
        echo "$MESSAGES" | jq -r '.[] |
            "--- " +
            (if .participant_type == "situation_builder" then "Situation Builder"
             elif .participant_type == "user" then "User"
             elif .agent_name then .agent_name
             else "Unknown" end) +
            " (" + .timestamp + ") ---\n" +
            (if .thinking and .thinking != "" and .thinking != null then
                "[Thinking]\n" + .thinking + "\n[/Thinking]\n\n"
             else "" end) +
            .content + "\n"' >> "$OUTPUT_FILE"

        # Update last message ID
        LAST_MESSAGE_ID=$(echo "$MESSAGES" | jq -r '.[-1].id')

        # Print progress
        echo -e "${GREEN}  Received $NEW_MESSAGE_COUNT new message(s) (total polls: $POLL_COUNT)${NC}"
    else
        # Increment no-new-message counter
        NO_NEW_MESSAGE_COUNT=$((NO_NEW_MESSAGE_COUNT + 1))

        # Check if conversation has ended (no new messages for a while)
        if [ $NO_NEW_MESSAGE_COUNT -ge $MAX_NO_NEW_MESSAGE ]; then
            echo -e "${BLUE}  No new messages for ${MAX_NO_NEW_MESSAGE} polls ($((MAX_NO_NEW_MESSAGE * POLL_INTERVAL)) seconds).${NC}"
            echo -e "${BLUE}  Conversation appears complete.${NC}"
            break
        fi
    fi

    # Wait before next poll
    sleep $POLL_INTERVAL
    POLL_COUNT=$((POLL_COUNT + 1))
done

# Add footer to transcript
cat >> "$OUTPUT_FILE" << EOF

================================================================================
Simulation Complete
Total Polls: $POLL_COUNT
End Time: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
================================================================================
EOF

echo ""
echo -e "${GREEN}=== Simulation Complete ===${NC}"
echo -e "Transcript saved to: ${BLUE}$OUTPUT_FILE${NC}"
if [ "$SAVE_CONFIG" = true ]; then
    echo -e "Configuration saved to: ${BLUE}${OUTPUT_FILE%.txt}_config.txt${NC}"
fi
echo -e "Room ID: ${BLUE}$ROOM_ID${NC} (you can view it in the web interface)"
echo ""
