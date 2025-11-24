"""
Agent configuration module for parsing agent config files.

This module provides functionality to parse agent configuration files from
markdown and manage configuration constants. Agent-specific configuration is
now injected through MCP tool descriptions (see agents/tools.py).
"""

from .constants import (
    DEFAULT_FALLBACK_PROMPT,
    get_base_system_prompt,
)
from .parser import list_available_configs, parse_agent_config

__all__ = [
    "parse_agent_config",
    "list_available_configs",
    "get_base_system_prompt",
    "DEFAULT_FALLBACK_PROMPT",
]
