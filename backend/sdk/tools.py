"""
Agent tools for controlling agent behavior.

This module re-exports all tool creation functions from specialized modules
for backward compatibility. New code should import directly from the specific
modules:
- action_tools: skip, memorize, recall tools (for chat agents)
- guidelines_tools: guidelines read tool (for chat agents)
- brain_tools: character config and memory selection tools (for memory brain agent)
- memory_brain_manager: SDK manager for memory brain agent
"""

# Re-export action tools
from sdk.action_tools import create_action_mcp_server, create_action_tools

# Re-export brain tools (for memory brain agent)
from sdk.brain_tools import (
    create_character_config_mcp_server,
    create_character_config_tool,
    create_memory_brain_mcp_server,
    create_memory_selection_tools,
)

# Re-export guidelines tools
from sdk.guidelines_tools import create_guidelines_mcp_server

# Re-export memory brain manager
from sdk.memory_brain_manager import MemoryBrainSDKManager

__all__ = [
    # Action tools (for chat agents)
    "create_action_tools",
    "create_action_mcp_server",
    # Guidelines tools (for chat agents)
    "create_guidelines_mcp_server",
    # Brain tools (for memory brain agent)
    "create_character_config_tool",
    "create_character_config_mcp_server",
    "create_memory_selection_tools",
    "create_memory_brain_mcp_server",
    # Memory brain manager
    "MemoryBrainSDKManager",
]
