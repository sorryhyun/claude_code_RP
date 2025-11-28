"""
YAML Configuration Loader - Compatibility Module

This module re-exports all configuration functions from the refactored modules
for backward compatibility. New code should import directly from:
- config.cache: Caching infrastructure
- config.loaders: Raw config file loaders
- config.tools: Tool descriptions, schemas, grouping
- config.memory: Memory brain prompts, policies
- config.validation: Schema validation, startup logging
"""

# Re-export from cache
from .cache import (
    _config_cache,
    _get_file_mtime,
    _load_yaml_file,
    clear_cache,
    get_cached_config,
)

# Re-export from loaders
from .loaders import (
    BRAIN_CONFIG,
    CONFIG_DIR,
    CONVERSATION_CONTEXT_CONFIG,
    DEBUG_CONFIG,
    GUIDELINES_CONFIG,
    TOOLS_CONFIG,
    get_brain_config,
    get_conversation_context_config,
    get_debug_config,
    get_guidelines_config,
    get_memory_context_config,
    get_memory_tools_config,
    get_tools_config,
)

# Re-export from memory
from .memory import (
    get_max_memories_default,
    get_memory_brain_prompt,
    get_memory_policy_prompt,
    get_memory_tool_description,
    get_memory_tool_input_schema,
    get_memory_tool_response,
)

# Re-export from tools
from .tools import (
    get_situation_builder_note,
    get_tool_description,
    get_tool_group,
    get_tool_input_schema,
    get_tool_names_by_group,
    get_tool_response,
    get_tools_by_group,
    is_tool_enabled,
)

# Re-export from validation
from .validation import (
    log_config_validation,
    reload_all_configs,
    validate_config_schema,
)

# Backward compatibility alias
_get_cached_config = get_cached_config

__all__ = [
    # Cache
    "_config_cache",
    "_get_file_mtime",
    "_load_yaml_file",
    "clear_cache",
    "get_cached_config",
    "_get_cached_config",
    # Loaders
    "CONFIG_DIR",
    "TOOLS_CONFIG",
    "GUIDELINES_CONFIG",
    "DEBUG_CONFIG",
    "CONVERSATION_CONTEXT_CONFIG",
    "BRAIN_CONFIG",
    "get_tools_config",
    "get_guidelines_config",
    "get_debug_config",
    "get_conversation_context_config",
    "get_brain_config",
    "get_memory_tools_config",
    "get_memory_context_config",
    # Tools
    "get_tool_description",
    "get_tool_input_schema",
    "get_tool_response",
    "get_situation_builder_note",
    "is_tool_enabled",
    "get_tools_by_group",
    "get_tool_names_by_group",
    "get_tool_group",
    # Memory
    "get_memory_brain_prompt",
    "get_memory_policy_prompt",
    "get_memory_tool_description",
    "get_memory_tool_input_schema",
    "get_memory_tool_response",
    "get_max_memories_default",
    # Validation
    "reload_all_configs",
    "validate_config_schema",
    "log_config_validation",
]
