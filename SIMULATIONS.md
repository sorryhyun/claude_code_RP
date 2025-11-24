# Simulations & Testing

Run automated chatroom simulations and agent tests using scripts in `scripts/`.

## Quick Start

### Run a Simulation

```bash
make simulate ARGS='--password "pass" --scenario "Discuss AI ethics" --agents "alice,bob"'

# Or directly:
./scripts/simulation/simulate_chatroom.sh -p "pass" -s "Discuss AI ethics" -a "alice,bob"
```

### Test Agents

```bash
make test-agents ARGS='10 alice bob charlie'  # 10 questions each

# Or directly:
./scripts/testing/test_agent_questions.sh 10 alice bob charlie
```

## Simulation Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--password` | `-p` | API password | From `.env` |
| `--scenario` | `-s` | Conversation scenario | Required |
| `--agents` | `-a` | Comma-separated agent names | Required |
| `--max-interactions` | `-m` | Max conversation rounds | `20` |
| `--output` | `-o` | Output filename | `chatroom_N.txt` |
| `--save-config` | - | Save system config to file | `false` |

**Examples:**

```bash
# Basic simulation
./scripts/simulation/simulate_chatroom.sh \
  -p "mypass" \
  -s "Plan a surprise birthday party" \
  -a "alice,bob,charlie"

# Custom config
./scripts/simulation/simulate_chatroom.sh \
  -p "mypass" \
  -s "Debate about consciousness" \
  -a "philosopher,scientist" \
  -m 30 \
  -o "consciousness_debate.txt" \
  --save-config
```

## Using JWT Tokens

Avoid re-authenticating by saving JWT token:

**Add to `.env`:**
```bash
JWT_TOKEN=your_token_here
```

The script will auto-load it. Or pass with `-t`:
```bash
./scripts/simulation/simulate_chatroom.sh -t "your_token" -s "..." -a "..."
```

## Output Files

**Transcript format:**
```
================================================================================
ChitChats Simulation Transcript
================================================================================
Room: Party Planning (ID: 123)
Agents: alice,bob,charlie
Scenario: Plan a surprise party
Timestamp: 2024-01-15 10:30:00 UTC
================================================================================

--- alice (2024-01-15T10:30:15Z) ---
[Thinking]
I should suggest a venue...
[/Thinking]

How about we do it at the park?

--- bob (2024-01-15T10:30:25Z) ---
Great idea! What about food?
...
```

**Config file** (with `--save-config`):
```
chatroom_debate_config.txt  # Contains system prompt, tools, agent configs
```

## Batch Simulations

Run multiple simulations in parallel:

```bash
# Example: scripts/simulation/simulation_1.sh
./scripts/simulation/simulate_chatroom.sh -s "Scenario 1" -a "alice,bob" &
./scripts/simulation/simulate_chatroom.sh -s "Scenario 2" -a "charlie,dave" &
wait
```

See `scripts/simulation/simulation_1.sh` for a full example with 7 parallel simulations.

## Agent Testing

Test individual agents with predefined questions:

**1. Create question file:**
```markdown
# agent_questions/alice.md
1. What is your favorite color?
2. How do you handle stress?
3. What are your long-term goals?
```

**2. Run test:**
```bash
./scripts/testing/test_agent_questions.sh 10 alice bob  # First 10 questions
```

**Output:**
```
test_alice_1234567890.txt
test_bob_1234567890.txt
```

## Prerequisites

- **Backend running:** `make run-backend` or `make dev`
- **jq installed:** `sudo apt-get install jq` (Ubuntu) or `brew install jq` (macOS)
- **Agents configured:** Agents must exist in `agents/` directory

## Troubleshooting

**"Authentication failed":**
- Check password is correct
- Verify `API_KEY_HASH` in `.env` matches your password

**"Agent not found":**
- Check agent name spelling
- Verify agent exists in `agents/` directory
- Restart backend to reload agents

**"No new messages":**
- Simulation auto-stops after 60 polls (2 min) of silence
- Increase `MAX_NO_NEW_MESSAGE` in script if needed

**Script errors:**
- Ensure `jq` is installed
- Check backend is running and accessible
- Verify network connectivity

## Advanced Usage

### Custom Backend URL

```bash
export BACKEND_URL="https://your-backend.com"
./scripts/simulation/simulate_chatroom.sh -s "..." -a "..."
```

### Save Password Securely

```bash
export CHITCHATS_PASSWORD="your_password"
# Password won't appear in shell history
./scripts/simulation/simulate_chatroom.sh -s "..." -a "..."
```

### Monitoring Long Simulations

```bash
# Run in background
./scripts/simulation/simulate_chatroom.sh -s "..." -a "..." &

# Monitor output
tail -f chatroom_1.txt
```

## Tips

- **Token reuse:** Save JWT token in `.env` to skip re-authentication
- **Parallel runs:** Stagger starts by 2-3 seconds to reduce backend load
- **Debugging:** Enable `DEBUG_AGENTS=true` in backend `.env` for detailed logs
- **Conversation length:** Agents auto-stop when conversation naturally ends
- **Config snapshots:** Use `--save-config` to preserve exact setup for reproducibility
