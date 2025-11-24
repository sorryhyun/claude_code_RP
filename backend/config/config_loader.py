"""
YAML Configuration Loader with Hot-Reloading

This module provides utilities for loading YAML configuration files with:
- File locking to prevent concurrent access issues
- Caching with automatic invalidation on file changes
- Environment variable overrides
- Template variable substitution
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ruamel.yaml import YAML
from services.memory_mode_service import get_memory_mode_service
from utils.file_locking import file_lock

yaml = YAML(typ="safe", pure=True)

logger = logging.getLogger(__name__)

# Configuration file paths
CONFIG_DIR = Path(__file__).parent / "tools"
TOOLS_CONFIG = CONFIG_DIR / "tools.yaml"
GUIDELINES_CONFIG = CONFIG_DIR / "guidelines_3rd.yaml"
DEBUG_CONFIG = CONFIG_DIR / "debug.yaml"
CONVERSATION_CONTEXT_CONFIG = CONFIG_DIR / "conversation_context.yaml"
BRAIN_CONFIG = CONFIG_DIR / "brain_config.yaml"

# Cache for loaded configurations
_config_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}


def _get_file_mtime(file_path: Path) -> float:
    """Get the modification time of a file."""
    try:
        return file_path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """
    Load a YAML file with file locking.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary containing the parsed YAML content
    """
    if not file_path.exists():
        logger.warning(f"Configuration file not found: {file_path}")
        return {}

    try:
        with file_lock(str(file_path), "r") as f:
            content = yaml.load(f)
            return content if content else {}
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}")
        return {}


def _get_cached_config(file_path: Path, force_reload: bool = False) -> Dict[str, Any]:
    """
    Get configuration from cache or reload if file has changed.

    Args:
        file_path: Path to the configuration file
        force_reload: Force reload even if cache is valid

    Returns:
        Configuration dictionary
    """
    cache_key = str(file_path)
    current_mtime = _get_file_mtime(file_path)

    # Check if cache is valid
    if not force_reload and cache_key in _config_cache:
        cached_mtime, cached_config = _config_cache[cache_key]
        if cached_mtime == current_mtime:
            return cached_config

    # Load fresh configuration
    config = _load_yaml_file(file_path)
    _config_cache[cache_key] = (current_mtime, config)

    logger.debug(f"Loaded configuration from {file_path}")
    return config


def get_tools_config() -> Dict[str, Any]:
    """
    Load the tools configuration from tools.yaml.

    Returns:
        Dictionary containing tool definitions
    """
    return _get_cached_config(TOOLS_CONFIG)


def get_guidelines_config() -> Dict[str, Any]:
    """
    Load the guidelines configuration from guidelines.yaml.

    Returns:
        Dictionary containing guideline templates
    """
    return _get_cached_config(GUIDELINES_CONFIG)


def get_debug_config() -> Dict[str, Any]:
    """
    Load the debug configuration from debug.yaml with environment variable overrides.

    Environment variables take precedence:
    - DEBUG_AGENTS=true overrides debug.enabled

    Returns:
        Dictionary containing debug settings
    """
    config = _get_cached_config(DEBUG_CONFIG)

    # Apply environment variable overrides
    if "debug" in config:
        # DEBUG_AGENTS environment variable overrides yaml setting
        debug_env = os.getenv("DEBUG_AGENTS", "").lower()
        if debug_env in ("true", "false"):
            config["debug"]["enabled"] = debug_env == "true"

    return config


def get_conversation_context_config() -> Dict[str, Any]:
    """
    Load the conversation context configuration from conversation_context.yaml.

    Returns:
        Dictionary containing conversation context templates
    """
    return _get_cached_config(CONVERSATION_CONTEXT_CONFIG)


def get_brain_config() -> Dict[str, Any]:
    """
    Load the brain configuration from brain_config.yaml (consolidated config).

    Returns:
        Dictionary containing memory tools, policies, and context templates
    """
    return _get_cached_config(BRAIN_CONFIG)


def get_memory_tools_config() -> Dict[str, Any]:
    """
    Load the memory tools configuration from brain_config.yaml.

    Returns:
        Dictionary containing memory tool definitions and policies
    """
    return get_brain_config()


def get_memory_context_config() -> Dict[str, Any]:
    """
    Load the memory context configuration from brain_config.yaml.

    Returns:
        Dictionary containing memory brain context templates
    """
    return get_brain_config()


def get_tool_description(
    tool_name: str,
    agent_name: str = "",
    config_sections: str = "",
    situation_builder_note: str = "",
    memory_subtitles: str = "",
) -> Optional[str]:
    """
    Get a tool description with template variables substituted.

    Args:
        tool_name: Name of the tool (skip, memorize, recall, guidelines, configuration)
        agent_name: Agent name to substitute in templates
        config_sections: Configuration sections for the configuration tool
        situation_builder_note: Situation builder note to include
        memory_subtitles: Available memory subtitles for the recall tool

    Returns:
        Tool description string with variables substituted, or None if tool not found
    """
    tools_config = get_tools_config()

    if "tools" not in tools_config or tool_name not in tools_config["tools"]:
        logger.warning(f"Tool '{tool_name}' not found in configuration")
        return None

    tool_config = tools_config["tools"][tool_name]

    # Check if tool is enabled
    if not tool_config.get("enabled", True):
        logger.debug(f"Tool '{tool_name}' is disabled in configuration")
        return None

    # Handle guidelines tool specially - it loads from a separate file
    if tool_name == "guidelines":
        guidelines_config = get_guidelines_config()
        active_version = guidelines_config.get("active_version", "v1")
        template = guidelines_config.get(active_version, {}).get("template", "")

        # Substitute template variables
        description = template.format(agent_name=agent_name, situation_builder_note=situation_builder_note)
        return description

    # For other tools, get description from tools.yaml
    description = tool_config.get("description", "")

    # Substitute template variables
    description = description.format(
        agent_name=agent_name,
        config_sections=config_sections,
        situation_builder_note=situation_builder_note,
        memory_subtitles=memory_subtitles,
    )

    return description


def get_tool_input_schema(tool_name: str) -> Dict[str, Any]:
    """
    Get the input schema for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Input schema dictionary
    """
    tools_config = get_tools_config()

    if "tools" not in tools_config or tool_name not in tools_config["tools"]:
        return {}

    return tools_config["tools"][tool_name].get("input_schema", {})


def get_tool_response(tool_name: str, **kwargs) -> str:
    """
    Get the response message for a tool with variables substituted.

    Args:
        tool_name: Name of the tool
        **kwargs: Variables to substitute in the response template

    Returns:
        Response string with variables substituted
    """
    tools_config = get_tools_config()

    if "tools" not in tools_config or tool_name not in tools_config["tools"]:
        return "Tool response not configured."

    response_template = tools_config["tools"][tool_name].get("response", "")

    try:
        return response_template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing variable in tool response template: {e}")
        return response_template


def get_situation_builder_note(has_situation_builder: bool) -> str:
    """
    Get the situation builder note if enabled and needed.

    Args:
        has_situation_builder: Whether the room has a situation builder agent

    Returns:
        Situation builder note string or empty string
    """
    if not has_situation_builder:
        return ""

    tools_config = get_tools_config()

    if "situation_builder" not in tools_config:
        return ""

    sb_config = tools_config["situation_builder"]

    if not sb_config.get("enabled", False):
        return ""

    return sb_config.get("template", "")


def is_tool_enabled(tool_name: str) -> bool:
    """
    Check if a tool is enabled in configuration.

    Memory mode (MEMORY_BY environment variable) controls recall tool:
    - RECALL mode: recall tool enabled, memory brain disabled
    - BRAIN mode: recall tool disabled, memory brain enabled

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is enabled, False otherwise
    """
    tools_config = get_tools_config()

    if "tools" not in tools_config or tool_name not in tools_config["tools"]:
        return False

    enabled = tools_config["tools"][tool_name].get("enabled", True)

    # Apply memory mode override for recall tool
    if tool_name == "recall":
        # Recall tool is ONLY enabled in RECALL mode
        memory_service = get_memory_mode_service()
        enabled = memory_service.is_recall_enabled(enabled)

    # Note: memorize tool (for recording memories) is available in both modes
    # and doesn't depend on MEMORY_MODE

    return enabled


def get_memory_brain_prompt(agent_name: str, max_memories: int, policy_section: str) -> str:
    """
    Get the memory-brain system prompt with template variables substituted.

    Character configuration (in_a_nutshell, characteristics) is provided via
    MCP tool descriptions, not in the system prompt.

    Args:
        agent_name: Agent name to substitute in template
        max_memories: Maximum number of memories to select
        policy_section: Policy-specific instructions

    Returns:
        Memory-brain system prompt with variables substituted
    """
    guidelines_config = get_guidelines_config()
    template = guidelines_config.get("memory_brain_prompt", "")

    if not template:
        logger.warning("memory_brain_prompt not found in guidelines configuration")
        return ""

    # Substitute template variables
    prompt = template.format(agent_name=agent_name, max_memories=max_memories, policy_section=policy_section)
    return prompt


def get_memory_policy_prompt(policy: str) -> str:
    """
    Get the policy-specific prompt section for memory brain.

    Args:
        policy: Policy name (balanced, trauma_biased, genius_planner, optimistic, avoidant)

    Returns:
        Policy-specific instructions as a string
    """
    memory_config = get_memory_tools_config()

    if "memory_policies" not in memory_config or policy not in memory_config["memory_policies"]:
        logger.warning(f"Memory policy '{policy}' not found in configuration, using 'balanced'")
        policy = "balanced"

    policy_data = memory_config["memory_policies"].get(policy, {})
    return policy_data.get("description", "")


def get_memory_tool_description(tool_name: str, max_memories: int = 3) -> Optional[str]:
    """
    Get a memory tool description with template variables substituted.

    Args:
        tool_name: Name of the tool (select_memory)
        max_memories: Maximum number of memories to select

    Returns:
        Tool description string with variables substituted, or None if tool not found
    """
    memory_config = get_memory_tools_config()

    if "memory_selection_tools" not in memory_config or tool_name not in memory_config["memory_selection_tools"]:
        logger.warning(f"Memory tool '{tool_name}' not found in configuration")
        return None

    tool_config = memory_config["memory_selection_tools"][tool_name]

    # Check if tool is enabled
    if not tool_config.get("enabled", True):
        logger.debug(f"Memory tool '{tool_name}' is disabled in configuration")
        return None

    description = tool_config.get("description", "")

    # Substitute template variables
    description = description.format(max_memories=max_memories)

    return description


def get_memory_tool_input_schema(tool_name: str) -> Dict[str, Any]:
    """
    Get the input schema for a memory tool.

    Args:
        tool_name: Name of the memory tool

    Returns:
        Input schema dictionary
    """
    memory_config = get_memory_tools_config()

    if "memory_selection_tools" not in memory_config or tool_name not in memory_config["memory_selection_tools"]:
        return {}

    return memory_config["memory_selection_tools"][tool_name].get("input_schema", {})


def get_memory_tool_response(tool_name: str, response_type: str = "success", **kwargs) -> str:
    """
    Get the response message for a memory tool with variables substituted.

    Args:
        tool_name: Name of the memory tool
        response_type: Type of response (success, error_invalid_strength, etc.)
        **kwargs: Variables to substitute in the response template

    Returns:
        Response string with variables substituted
    """
    memory_config = get_memory_tools_config()

    if "memory_selection_tools" not in memory_config or tool_name not in memory_config["memory_selection_tools"]:
        return "Memory tool response not configured."

    tool_config = memory_config["memory_selection_tools"][tool_name]
    responses = tool_config.get("responses", {})
    response_template = responses.get(response_type, "")

    if not response_template:
        logger.warning(f"Response type '{response_type}' not found for memory tool '{tool_name}'")
        return "Response not configured."

    try:
        return response_template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing variable in memory tool response template: {e}")
        return response_template


def get_max_memories_default() -> int:
    """
    Get the default maximum number of memories from configuration.

    Returns:
        Default max_memories value
    """
    memory_config = get_memory_tools_config()
    return memory_config.get("defaults", {}).get("max_memories", 3)


def get_tools_by_group(group_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all tools that belong to a specific group.

    Args:
        group_name: Name of the group (e.g., "action", "character")

    Returns:
        Dictionary mapping tool names (short names like "skip", "memorize") to their config
    """
    tools_config = get_tools_config()

    if "tools" not in tools_config:
        return {}

    tools_in_group = {}
    for tool_name, tool_config in tools_config["tools"].items():
        if tool_config.get("group") == group_name:
            tools_in_group[tool_name] = tool_config

    return tools_in_group


def get_tool_names_by_group(group_name: str, enabled_only: bool = True) -> list[str]:
    """
    Get full MCP tool names for all tools in a specific group.

    Args:
        group_name: Name of the group (e.g., "action", "character")
        enabled_only: Only return enabled tools (default: True)

    Returns:
        List of full MCP tool names (e.g., ["mcp__action__skip", "mcp__action__memorize"])
    """
    tools_in_group = get_tools_by_group(group_name)

    tool_names = []
    for tool_name, tool_config in tools_in_group.items():
        # Check if tool is enabled (if enabled_only is True)
        if enabled_only and not is_tool_enabled(tool_name):
            continue

        # Get the full MCP name
        mcp_name = tool_config.get("name")
        if mcp_name:
            tool_names.append(mcp_name)

    return tool_names


def get_tool_group(tool_name: str) -> Optional[str]:
    """
    Get the group name for a specific tool.

    Args:
        tool_name: Name of the tool (short name like "skip" or "memorize")

    Returns:
        Group name (e.g., "action", "character") or None if not found
    """
    tools_config = get_tools_config()

    if "tools" not in tools_config or tool_name not in tools_config["tools"]:
        return None

    return tools_config["tools"][tool_name].get("group")


def reload_all_configs():
    """Force reload all configuration files by clearing the cache."""
    global _config_cache
    _config_cache.clear()
    logger.info("Reloaded all configuration files")


def validate_config_schema() -> list[str]:
    """
    Validate configuration files have required keys and structure.

    Returns:
        List of validation errors (empty if all valid)
    """
    errors = []

    # Validate tools.yaml
    tools_config = get_tools_config()
    if not tools_config:
        errors.append("tools.yaml is empty or missing")
    elif "tools" not in tools_config:
        errors.append("tools.yaml missing 'tools' section")
    else:
        # Check for required tools
        required_tools = ["skip", "memorize", "recall", "guidelines", "configuration"]
        for tool_name in required_tools:
            if tool_name not in tools_config["tools"]:
                errors.append(f"tools.yaml missing required tool: {tool_name}")
            else:
                tool = tools_config["tools"][tool_name]
                # Validate tool structure
                if "name" not in tool:
                    errors.append(f"tools.yaml tool '{tool_name}' missing 'name' field")
                if "description" not in tool:
                    errors.append(f"tools.yaml tool '{tool_name}' missing 'description' field")

    # Validate guidelines_3rd.yaml
    guidelines_config = get_guidelines_config()
    if not guidelines_config:
        errors.append("guidelines_3rd.yaml is empty or missing")
    elif "active_version" not in guidelines_config:
        errors.append("guidelines_3rd.yaml missing 'active_version' field")
    else:
        active_version = guidelines_config.get("active_version")
        if active_version not in guidelines_config:
            errors.append(f"guidelines_3rd.yaml missing version section: {active_version}")
        else:
            version_config = guidelines_config[active_version]
            if "template" not in version_config:
                errors.append(f"guidelines_3rd.yaml version '{active_version}' missing 'template' field")

    # Validate debug.yaml
    debug_config = get_debug_config()
    if not debug_config:
        errors.append("debug.yaml is empty or missing")
    elif "debug" not in debug_config:
        errors.append("debug.yaml missing 'debug' section")

    # Validate conversation_context.yaml
    context_config = get_conversation_context_config()
    if not context_config:
        errors.append("conversation_context.yaml is empty or missing")

    # Validate brain_config.yaml
    brain_config = get_brain_config()
    if not brain_config:
        errors.append("brain_config.yaml is empty or missing")

    return errors


def log_config_validation():
    """
    Validate and log configuration status at startup.

    This should be called once during application initialization.
    """
    logger.info("🔧 Validating YAML configuration files...")

    errors = validate_config_schema()

    if errors:
        logger.error("❌ Configuration validation failed:")
        for error in errors:
            logger.error(f"   - {error}")
        logger.error("💡 Fix configuration files in backend/config/tools/")
    else:
        logger.info("✅ All configuration files validated successfully")

    # Log active configuration settings
    tools_config = get_tools_config()
    guidelines_config = get_guidelines_config()

    active_version = guidelines_config.get("active_version", "unknown")
    logger.info(f"📋 Active guidelines version: {active_version}")

    # Count enabled tools
    if "tools" in tools_config:
        enabled_tools = [name for name in tools_config["tools"].keys() if is_tool_enabled(name)]
        logger.info(f"🛠️  Enabled tools: {len(enabled_tools)}/{len(tools_config['tools'])} ({', '.join(enabled_tools)})")
