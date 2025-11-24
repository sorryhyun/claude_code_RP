"""
Memory mode service for centralized memory system configuration.

This module provides a service layer that manages memory mode switching and configuration.
Consumers should use this service instead of reading environment variables directly.
"""

import logging
from enum import Enum
from typing import Optional

from core.settings import get_settings

logger = logging.getLogger("MemoryModeService")


class MemoryMode(str, Enum):
    """Memory system mode enumeration."""

    RECALL = "RECALL"  # On-demand memory retrieval via recall tool
    BRAIN = "BRAIN"  # Automatic memory surfacing via memory brain


class MemoryModeService:
    """
    Service for managing memory mode configuration.

    This service provides centralized access to memory mode settings and
    ensures consistent behavior across the application.

    Memory modes:
    - RECALL: On-demand memory retrieval. Agents use the recall tool to fetch memories.
              Lower baseline token cost. Memory subtitles shown in context.
    - BRAIN: Automatic memory surfacing. Separate memory brain agent injects memories.
             Higher baseline token cost. Context-driven memory activation.

    Configuration:
    - Active mode: Controlled by MEMORY_BY environment variable
    - Memory file: Controlled by RECALL_MEMORY_FILE environment variable
    - Per-agent settings: Configured via agent's memory_brain.md file
    """

    def __init__(self):
        """Initialize memory mode service."""
        self._settings = get_settings()
        self._log_configuration()

    def _log_configuration(self):
        """Log memory mode configuration on initialization."""
        logger.info(f"Memory mode: {self.mode.value}")
        logger.info(f"Recall memory file: {self.memory_file}")

    @property
    def mode(self) -> MemoryMode:
        """
        Get the active memory mode.

        Returns:
            MemoryMode enum value (RECALL or BRAIN)
        """
        return MemoryMode(self._settings.memory_by)

    @property
    def memory_file(self) -> str:
        """
        Get the memory file name to use.

        Returns:
            Memory file name (without .md extension)
        """
        return self._settings.recall_memory_file

    @property
    def is_recall_mode(self) -> bool:
        """Check if in RECALL mode."""
        return self.mode == MemoryMode.RECALL

    @property
    def is_brain_mode(self) -> bool:
        """Check if in BRAIN mode."""
        return self.mode == MemoryMode.BRAIN

    def is_recall_enabled(self, tool_enabled_in_config: bool = True) -> bool:
        """
        Check if the recall tool should be enabled.

        The recall tool is only available in RECALL mode.

        Args:
            tool_enabled_in_config: Whether the tool is enabled in tools.yaml

        Returns:
            True if recall tool should be enabled
        """
        return self.is_recall_mode and tool_enabled_in_config

    def is_memory_brain_enabled(self, agent_memory_brain_enabled: bool = False) -> bool:
        """
        Check if memory brain should be enabled for a specific agent.

        Memory brain is only active in BRAIN mode AND when the agent has
        memory_brain.md configured with enabled: true.

        Args:
            agent_memory_brain_enabled: Whether agent's memory_brain.md has enabled: true

        Returns:
            True if memory brain should be used for this agent
        """
        return self.is_brain_mode and agent_memory_brain_enabled

    def invalidate_caches_on_mode_change(self):
        """
        Invalidate relevant caches when memory mode changes at runtime.

        This should be called if the memory mode is changed dynamically
        (e.g., via an admin endpoint) to ensure consistent behavior.

        Note: Currently, memory mode is set at startup via environment variables
        and does not change at runtime. This method is provided for future use.
        """
        from services.cache_service import get_cache_service

        cache_service = get_cache_service()

        # Invalidate all agent configs since they may have different memory settings
        cache_service.invalidate_pattern("agent_config:")
        cache_service.invalidate_pattern("agent_obj:")

        logger.info(f"Invalidated caches due to memory mode change to {self.mode.value}")


# Global memory mode service instance
_memory_mode_service: Optional[MemoryModeService] = None


def get_memory_mode_service() -> MemoryModeService:
    """Get the global memory mode service instance."""
    global _memory_mode_service
    if _memory_mode_service is None:
        _memory_mode_service = MemoryModeService()
    return _memory_mode_service


def reset_memory_mode_service():
    """Reset the memory mode service instance (useful for testing)."""
    global _memory_mode_service
    _memory_mode_service = None
