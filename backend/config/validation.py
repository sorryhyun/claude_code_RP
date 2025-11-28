"""
Configuration validation and logging.

Provides functions for validating configuration schema and startup logging.
"""

import logging
import os

from .cache import clear_cache
from .loaders import (
    get_brain_config,
    get_conversation_context_config,
    get_debug_config,
    get_guidelines_config,
    get_tools_config,
)
from .tools import is_tool_enabled

logger = logging.getLogger(__name__)


def reload_all_configs():
    """Force reload all configuration files by clearing the cache."""
    clear_cache()
    logger.info("Reloaded all configuration files")


def _get_memory_mode() -> str:
    """Get the current memory mode from environment."""
    mode = os.getenv("MEMORY_BY", "RECALL").upper()
    if mode not in ("RECALL", "BRAIN"):
        return "RECALL"
    return mode


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
        required_tools = ["skip", "memorize", "recall", "guidelines"]
        for tool_name in required_tools:
            if tool_name not in tools_config["tools"]:
                errors.append(f"tools.yaml missing required tool: {tool_name}")
            else:
                tool = tools_config["tools"][tool_name]
                # Validate tool structure
                if "name" not in tool:
                    errors.append(f"tools.yaml tool '{tool_name}' missing 'name' field")
                # Tools must have either 'description' or 'source' (for loading from separate file)
                if "description" not in tool and "source" not in tool:
                    errors.append(f"tools.yaml tool '{tool_name}' missing 'description' or 'source' field")

    # Validate guidelines_3rd.yaml
    guidelines_config = get_guidelines_config()
    if not guidelines_config:
        errors.append("guidelines_3rd.yaml is empty or missing")
    else:
        # Check for active_version (guidelines template)
        if "active_version" not in guidelines_config:
            errors.append("guidelines_3rd.yaml missing 'active_version' field")
        else:
            active_version = guidelines_config.get("active_version")
            if active_version not in guidelines_config:
                errors.append(f"guidelines_3rd.yaml missing version section: {active_version}")
            else:
                version_config = guidelines_config[active_version]
                if "template" not in version_config:
                    errors.append(f"guidelines_3rd.yaml version '{active_version}' missing 'template' field")

        # Check for system_prompt
        active_system_prompt = guidelines_config.get("active_system_prompt", "system_prompt")
        if active_system_prompt not in guidelines_config:
            errors.append(f"guidelines_3rd.yaml missing system prompt: '{active_system_prompt}'")

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
    else:
        # Validate memory policies if in BRAIN mode
        memory_mode = _get_memory_mode()
        if memory_mode == "BRAIN":
            if "memory_policies" not in brain_config:
                errors.append("brain_config.yaml missing 'memory_policies' section (required for MEMORY_BY=BRAIN)")
            else:
                # Check for at least 'balanced' policy
                if "balanced" not in brain_config["memory_policies"]:
                    errors.append("brain_config.yaml missing required 'balanced' memory policy")

        # Validate memory selection tools
        if "memory_selection_tools" in brain_config:
            for tool_name, tool_config in brain_config["memory_selection_tools"].items():
                if "description" not in tool_config:
                    errors.append(f"brain_config.yaml memory tool '{tool_name}' missing 'description' field")

        # Validate defaults
        if "defaults" not in brain_config:
            errors.append("brain_config.yaml missing 'defaults' section")

    return errors


def log_config_validation():
    """
    Validate and log configuration status at startup.

    This should be called once during application initialization.
    """
    logger.info("Validating YAML configuration files...")

    errors = validate_config_schema()

    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"   - {error}")
        logger.error("Fix configuration files in backend/config/tools/")
    else:
        logger.info("All configuration files validated successfully")

    # Log active configuration settings
    tools_config = get_tools_config()
    guidelines_config = get_guidelines_config()
    brain_config = get_brain_config()

    # Guidelines info
    active_version = guidelines_config.get("active_version", "unknown")
    logger.info(f"Active guidelines version: {active_version}")

    # System prompt info
    active_system_prompt = guidelines_config.get("active_system_prompt", "system_prompt")
    logger.info(f"Active system prompt: {active_system_prompt}")

    # Memory mode info
    memory_mode = _get_memory_mode()
    if memory_mode == "RECALL":
        logger.info("Memory mode: RECALL (on-demand retrieval via recall tool)")
    else:
        logger.info("Memory mode: BRAIN (automatic memory surfacing)")
        # Log memory defaults if available
        if brain_config and "defaults" in brain_config:
            max_memories = brain_config["defaults"].get("max_memories", 3)
            logger.info(f"   Max memories per turn: {max_memories}")

    # Count enabled tools
    if "tools" in tools_config:
        enabled_tools = [name for name in tools_config["tools"].keys() if is_tool_enabled(name)]
        logger.info(f"Enabled tools: {len(enabled_tools)}/{len(tools_config['tools'])} ({', '.join(enabled_tools)})")

    # Debug mode info
    debug_config = get_debug_config()
    if debug_config and debug_config.get("debug", {}).get("enabled"):
        logger.info("Debug logging: ENABLED")


__all__ = [
    "reload_all_configs",
    "validate_config_schema",
    "log_config_validation",
]
