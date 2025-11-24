"""
Guidelines tools for agent behavioral guidance.

This module defines MCP tools for guidelines injection:
- DESCRIPTION mode: Guidelines passively injected via tool description
- ACTIVE_TOOL mode: Agents actively call mcp__guidelines__read to retrieve guidelines
"""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from config.config_loader import (
    get_situation_builder_note,
    get_tool_description,
    get_tool_input_schema,
    get_tool_response,
    is_tool_enabled,
)
from config.parser import GUIDELINE_READ_MODE


def _create_guidelines_description_tool(agent_name: str, guidelines_content: str):
    """Create guidelines tool for DESCRIPTION mode (passive injection)."""
    guidelines_schema = get_tool_input_schema("guidelines")

    @tool("guidelines", guidelines_content, guidelines_schema)
    async def role_guidelines_tool(_args: dict[str, Any]):
        """This tool should never be called - it exists only to inject role guidelines."""
        response = get_tool_response("guidelines")
        return {"content": [{"type": "text", "text": response}]}

    return role_guidelines_tool


def _create_guidelines_read_tool(agent_name: str, guidelines_content: str):
    """Create callable read tool for ACTIVE_TOOL mode."""
    description = get_tool_description("read", agent_name=agent_name)
    schema = get_tool_input_schema("read")

    @tool("read", description, schema)
    async def read_tool(_args: dict[str, Any]):
        """Callable tool that returns the complete guidelines when called by the agent."""
        return {"content": [{"type": "text", "text": guidelines_content}]}

    return read_tool


def create_guidelines_mcp_server(agent_name: str, has_situation_builder: bool = False):
    """
    Create an MCP server with guidelines tools based on GUIDELINE_READ_MODE.

    - DESCRIPTION mode: Creates passive injection tool (guidelines in tool description)
    - ACTIVE_TOOL mode: Creates read tool (agents call mcp__guidelines__read)

    Args:
        agent_name: The name of the agent
        has_situation_builder: Whether the room has a situation builder agent

    Returns:
        MCP server instance with guidelines tools
    """
    # Get situation builder note from configuration
    situation_builder_note = get_situation_builder_note(has_situation_builder)

    # Get the full guidelines content
    guidelines_content = get_tool_description(
        "guidelines", agent_name=agent_name, situation_builder_note=situation_builder_note
    )

    # Create appropriate tools based on mode
    tools = []

    if GUIDELINE_READ_MODE == "description":
        # DESCRIPTION mode: Passive injection via tool description
        if is_tool_enabled("guidelines"):
            tools.append(_create_guidelines_description_tool(agent_name, guidelines_content))
    else:
        # ACTIVE_TOOL mode (default): Agents call read tool
        if is_tool_enabled("read"):
            tools.append(_create_guidelines_read_tool(agent_name, guidelines_content))

    return create_sdk_mcp_server(name="guidelines", version="1.0.0", tools=tools)
