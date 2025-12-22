"""
Agent management module for Claude SDK integration.

This module provides the AgentManager class and related utilities for
managing agent lifecycle, response generation, and debugging.
"""

from infrastructure.logging.formatters import format_message_for_debug

from .action_tools import create_action_mcp_server
from .manager import AgentManager

__all__ = [
    "AgentManager",
    "create_action_mcp_server",
    "format_message_for_debug",
]
