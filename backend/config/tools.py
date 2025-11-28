"""
Tool configuration functions.

Provides functions to get tool descriptions, schemas, and groupings.
"""

import logging
from typing import Any, Dict, Optional

from services.memory_mode_service import get_memory_mode_service

from .loaders import get_guidelines_config, get_tools_config

logger = logging.getLogger(__name__)


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


__all__ = [
    "get_tool_description",
    "get_tool_input_schema",
    "get_tool_response",
    "get_situation_builder_note",
    "is_tool_enabled",
    "get_tools_by_group",
    "get_tool_names_by_group",
    "get_tool_group",
]
