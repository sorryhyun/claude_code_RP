"""
Memory configuration functions.

Provides functions for memory brain prompts, policies, and memory tools.
"""

import logging
from typing import Any, Dict, Optional

from .loaders import get_guidelines_config, get_memory_tools_config

logger = logging.getLogger(__name__)


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


__all__ = [
    "get_memory_brain_prompt",
    "get_memory_policy_prompt",
    "get_memory_tool_description",
    "get_memory_tool_input_schema",
    "get_memory_tool_response",
    "get_max_memories_default",
]
