"""
Memory brain tools for memory selection and character configuration.

This module defines MCP tools used exclusively by the memory brain agent:
- Character configuration tools: Inject agent identity via tool descriptions
- Memory selection tools: Allow brain to select which memories should surface

These tools are NOT used by regular chat agents. Chat agents use action_tools.py
(skip, memorize, recall) instead.
"""

from typing import Any, Dict, List, Optional

from claude_agent_sdk import create_sdk_mcp_server, tool
from config.config_loader import get_memory_tool_description, get_memory_tool_input_schema, get_memory_tool_response
from domain.memory import MemoryBrainOutput


def create_character_config_tool(
    agent_name: str, in_a_nutshell: Optional[str] = None, characteristics: Optional[str] = None
) -> list:
    """
    Create MCP tools that inject character configuration for memory brain.

    This tool is not meant to be called - it exists solely to inject character
    configuration through tool description, similar to how regular agents work.

    Args:
        agent_name: The name of the agent
        in_a_nutshell: Brief identity summary
        characteristics: Personality traits

    Returns:
        List containing the character configuration tool
    """
    tools = []

    # Build configuration sections
    config_sections = []

    if in_a_nutshell:
        config_sections.append(f"<in_a_nutshell> {in_a_nutshell} </in_a_nutshell>")

    if characteristics:
        config_sections.append(f"<characteristics> {characteristics} </characteristics>")

    if config_sections:
        config_sections_str = "\n".join(config_sections)
        description = f"""<character_configuration> {agent_name}'s identity:
{config_sections_str}

This defines {agent_name}'s core identity. Use this to understand how {agent_name} thinks and what triggers {agent_name}'s memories. </character_configuration>"""

        @tool("character_identity", description, {})
        async def character_identity_tool(_args: Dict) -> Dict:
            """This tool should never be called - it exists only to inject character configuration."""
            _ = _args  # Explicitly mark as intentionally unused
            return {"content": [{"type": "text", "text": "This tool exists only to provide character configuration."}]}

        tools.append(character_identity_tool)

    return tools


def create_memory_selection_tools(
    available_memories: List[Dict[str, Any]], max_memories: int = 3
) -> tuple[list, callable]:
    """
    Create MCP tools for memory selection.

    Tool descriptions and responses are loaded from memory_tools.yaml configuration.

    Returns:
        tuple: (list of tool functions, function to get final result)

    The tool allows the memory brain agent to:
    - Select individual memories with activation strength and reasoning (up to max_memories)
    - Auto-determines should_inject_now based on whether any memories were selected

    Usage:
        tools, get_result = create_memory_selection_tools(memories)
        # Pass tools to agent
        # After agent runs, call get_result() to get MemoryBrainOutput
    """
    # Session state for collecting selections
    state = {"selected_memories": []}

    # Load tool configurations
    select_description = get_memory_tool_description("select_memory", max_memories)
    select_schema = get_memory_tool_input_schema("select_memory")

    @tool("select_memory", select_description, select_schema)
    async def select_memory(args: Dict) -> Dict:
        """Tool for selecting a memory."""
        memory_id = args["memory_id"]
        activation_strength = args["activation_strength"]
        reason = args["reason"]

        # Validate activation strength
        if not (0.0 <= activation_strength <= 1.0):
            response = get_memory_tool_response(
                "select_memory", "error_invalid_strength", activation_strength=activation_strength
            )
            return {"content": [{"type": "text", "text": response}]}

        # Check if already at max
        if len(state["selected_memories"]) >= max_memories:
            response = get_memory_tool_response("select_memory", "error_max_reached", max_memories=max_memories)
            return {"content": [{"type": "text", "text": response}]}

        # Check if memory exists
        if not any(m["id"] == memory_id for m in available_memories):
            response = get_memory_tool_response("select_memory", "error_not_found", memory_id=memory_id)
            return {"content": [{"type": "text", "text": response}]}

        # Check if already selected
        if any(m["memory_id"] == memory_id for m in state["selected_memories"]):
            response = get_memory_tool_response("select_memory", "error_already_selected", memory_id=memory_id)
            return {"content": [{"type": "text", "text": response}]}

        # Add to selections
        state["selected_memories"].append(
            {"memory_id": memory_id, "activation_strength": activation_strength, "reason": reason}
        )

        remaining = max_memories - len(state["selected_memories"])
        response = get_memory_tool_response(
            "select_memory",
            "success",
            memory_id=memory_id,
            activation_strength=activation_strength,
            remaining=remaining,
        )
        return {"content": [{"type": "text", "text": response}]}

    def get_result() -> "MemoryBrainOutput":
        """Get the final MemoryBrainOutput from collected tool calls."""
        from domain.memory import MemoryActivation, MemoryBrainOutput

        activations = [
            MemoryActivation(memory_id=m["memory_id"], activation_strength=m["activation_strength"], reason=m["reason"])
            for m in state["selected_memories"]
        ]

        # Auto-determine should_inject_now: inject if any memories were selected
        should_inject = len(activations) > 0

        return MemoryBrainOutput(
            should_inject_now=should_inject,
            activated_memories=activations,
            reasoning="",  # No longer needed without finalize_selection tool
        )

    return [select_memory], get_result


def create_character_config_mcp_server(
    agent_name: str, in_a_nutshell: Optional[str] = None, characteristics: Optional[str] = None
):
    """
    Create an MCP server with memory brain character configuration tools.

    Args:
        agent_name: The name of the agent
        in_a_nutshell: Brief identity summary
        characteristics: Personality traits

    Returns:
        MCP server instance with character configuration tools
    """
    config_tools = create_character_config_tool(
        agent_name=agent_name, in_a_nutshell=in_a_nutshell, characteristics=characteristics
    )

    return create_sdk_mcp_server(name="character", version="1.0.0", tools=config_tools)


def create_memory_brain_mcp_server(available_memories: List[Dict[str, Any]], max_memories: int = 3) -> tuple:
    """
    Create an MCP server with memory selection tools.

    This creates the MCP server for memory brain's selection tools only.
    Config tools should be added separately via create_character_config_mcp_server.

    Args:
        available_memories: List of available long-term memory entries
        max_memories: Maximum number of memories to surface per turn

    Returns:
        Tuple of (MCP server instance, function to get result)
    """
    # Create memory selection tools
    selection_tools, get_result = create_memory_selection_tools(
        available_memories=available_memories, max_memories=max_memories
    )

    # Create MCP server
    mcp_server = create_sdk_mcp_server(name="memory_brain", version="1.0.0", tools=selection_tools)

    return mcp_server, get_result
