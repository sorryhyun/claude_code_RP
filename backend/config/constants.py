"""
Configuration constants for agent config file parsing.

This module defines default prompts and other constants
used in parsing and building agent configurations.
"""

# Default fallback prompt if no configuration is provided
DEFAULT_FALLBACK_PROMPT = "You are a helpful AI assistant."


def get_base_system_prompt() -> str:
    """
    Load the base system prompt from guidelines.yaml.
    This allows dynamic updates without server restart.

    Character configuration is always appended to the system prompt with markdown headings.

    Returns:
        The system prompt template with {agent_name} placeholder
    """
    try:
        # Import here to avoid circular dependency
        from config.config_loader import get_guidelines_config

        guidelines_config = get_guidelines_config()

        # Always use system_prompt (character config in system prompt with markdown)
        system_prompt = guidelines_config.get("system_prompt", "")

        if system_prompt:
            return system_prompt.strip()
        else:
            import logging

            logging.warning("system_prompt not found in guidelines.yaml, using fallback")
            return DEFAULT_FALLBACK_PROMPT
    except Exception as e:
        # Log and use fallback on any error
        import logging

        logging.error(f"Error loading system prompt from guidelines.yaml: {e}")
        return DEFAULT_FALLBACK_PROMPT


# Skip message text (displayed when agent chooses not to respond)
SKIP_MESSAGE_TEXT = "(무시함)"

# Claude Agent SDK Tool Configuration
# These are the built-in tools provided by Claude Agent SDK that we want to disallow
# to ensure agents stay in character and use only their character-specific tools
BUILTIN_TOOLS = [
    "Task",
    "Bash",
    "Glob",
    "Grep",
    "ExitPlanMode",
    "Read",
    "Edit",
    "Write",
    "NotebookEdit",
    "WebFetch",
    "TodoWrite",
    "WebSearch",
    "BashOutput",
    "KillShell",
    "Skill",
    "SlashCommand",
]

# Character-specific MCP tool names organized by group
# These are the tools available to each agent for character-based interactions
AGENT_TOOL_NAMES_BY_GROUP = {
    "action": {
        "skip": "mcp__action__skip",
        "memorize": "mcp__action__memorize",
        "recall": "mcp__action__recall",
    },
    "character": {
        "guidelines": "mcp__character__guidelines",
        "guidelines_read": "mcp__guidelines__read",
        "memory_select": "mcp__character__character_identity",
    },
    "memory_brain": {
        "memory_config": "mcp__memory_brain__select_memory",
    },
}

# Backward compatibility: Flat dictionary for legacy code
AGENT_TOOL_NAMES = {
    tool_key: tool_name
    for group_tools in AGENT_TOOL_NAMES_BY_GROUP.values()
    for tool_key, tool_name in group_tools.items()
}

# Thinking Tokens Configuration
# Maximum number of thinking tokens for agent responses
# Can be overridden by MAX_THINKING_TOKENS environment variable
import os

MAX_THINKING_TOKENS = int(os.getenv("MAX_THINKING_TOKENS", "32768"))
MEMORY_BRAIN_MAX_THINKING_TOKENS = int(os.getenv("MEMORY_BRAIN_MAX_THINKING_TOKENS", "2048"))
