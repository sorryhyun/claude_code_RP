"""
Agent configuration parser for markdown files.

This module handles loading agent configurations from markdown files
following a specific format with standardized sections.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from core import get_settings
from domain.agent_config import AgentConfigData
from domain.memory import MemoryPolicy
from utils.memory_parser import parse_long_term_memory

logger = logging.getLogger("ConfigParser")

# Get settings singleton
_settings = get_settings()

# Get memory mode service
from services.memory_mode_service import get_memory_mode_service

_memory_service = get_memory_mode_service()

# Global configuration from settings (kept for backwards compatibility)
# New code should use get_memory_mode_service() directly
MEMORY_MODE = _memory_service.mode.value
RECALL_MEMORY_FILE = _memory_service.memory_file
GUIDELINE_READ_MODE = _settings.read_guideline_by

# Log configuration (memory mode is logged by the service)
logger.info(f"Guideline read mode: {GUIDELINE_READ_MODE}")


def parse_agent_config(file_path: str) -> Optional[AgentConfigData]:
    """
    Parse an agent configuration from a folder with separate markdown files.

    Expected folder structure:
       agents/agent_name/
         ├── in_a_nutshell.md
         ├── characteristics.md
         ├── recent_events.md
         └── consolidated_memory.md (or long_term_memory.md)

    Args:
        file_path: Path to the agent folder (can be relative to project root)

    Returns:
        AgentConfigData object or None if folder doesn't exist
    """
    # Resolve path relative to project root if not absolute
    path = Path(file_path)
    if not path.is_absolute():
        backend_dir = Path(__file__).parent.parent
        project_root = backend_dir.parent
        path = project_root / file_path

    if not path.exists() or not path.is_dir():
        return None

    try:
        return _parse_folder_config(path)
    except Exception as e:
        logger.error(f"Error parsing agent config {path}: {e}")
        return None


def _parse_folder_config(folder_path: Path) -> AgentConfigData:
    """Parse agent configuration from folder with separate .md files."""

    def read_section(filename: str) -> str:
        file_path = folder_path / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def find_profile_pic() -> Optional[str]:
        """Find profile picture file in the agent folder."""
        # Common image extensions to look for
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]
        # Common profile pic filenames
        common_names = ["profile", "avatar", "picture", "photo"]

        # First, try common profile pic filenames
        for name in common_names:
            for ext in image_extensions:
                pic_path = folder_path / f"{name}{ext}"
                if pic_path.exists():
                    return pic_path.name

        # If no common name found, look for any image file
        for ext in image_extensions:
            for file in folder_path.glob(f"*{ext}"):
                return file.name

        return None

    # Parse long-term memory file based on environment configuration
    # Support both "long_term_memory.md" and "consolidated_memory.md"
    memory_filename = f"{RECALL_MEMORY_FILE}.md"
    long_term_memory_file = folder_path / memory_filename
    long_term_memory_index = None
    long_term_memory_subtitles = None
    memory_brain_enabled = False
    memory_brain_policy = "balanced"

    # GLOBAL OVERRIDE: MEMORY_MODE determines which system to use
    # This overrides per-agent memory_brain.md configurations
    if MEMORY_MODE == "RECALL":
        # RECALL MODE: Load memory index for recall tool, disable memory brain
        if long_term_memory_file.exists():
            long_term_memory_index = parse_long_term_memory(long_term_memory_file)
            if long_term_memory_index:
                # Create a comma-separated list of subtitles for context injection
                long_term_memory_subtitles = ", ".join(f"'{s}'" for s in long_term_memory_index.keys())
        # Memory brain is always disabled in RECALL mode (global override)
        memory_brain_enabled = False

    elif MEMORY_MODE == "BRAIN":
        # BRAIN MODE: Load memory index for brain, check if brain config exists
        if long_term_memory_file.exists():
            long_term_memory_index = parse_long_term_memory(long_term_memory_file)
            if long_term_memory_index:
                logger.debug(
                    f"[BRAIN MODE] Loaded {len(long_term_memory_index)} long-term memories from {folder_path.name}/{memory_filename}"
                )

        # Parse memory-brain configuration from memory_brain.md
        memory_brain_file = folder_path / "memory_brain.md"
        if memory_brain_file.exists():
            memory_brain_content = read_section("memory_brain.md").lower()
            # Check if memory-brain is enabled
            if "enabled: true" in memory_brain_content or "enabled:true" in memory_brain_content:
                memory_brain_enabled = True
                # Extract policy (look for "policy: <value>")
                for line in memory_brain_content.split("\n"):
                    if "policy:" in line:
                        policy = line.split("policy:")[1].strip()
                        if policy in ["balanced", "trauma_biased", "genius_planner", "optimistic", "avoidant"]:
                            memory_brain_policy = policy
                        break
                logger.debug(
                    f"[BRAIN MODE] Memory brain enabled for {folder_path.name} with policy: {memory_brain_policy}"
                )
            else:
                logger.debug(f"[BRAIN MODE] Memory brain config exists but not enabled for {folder_path.name}")
        else:
            # In BRAIN mode, if no memory_brain.md exists, we can still use default settings
            # But let's not enable it by default - only if explicitly configured
            logger.debug(f"[BRAIN MODE] No memory_brain.md found for {folder_path.name}, memory brain disabled")

    # Convert string policy to MemoryPolicy enum
    policy_enum = MemoryPolicy.BALANCED
    try:
        policy_enum = MemoryPolicy(memory_brain_policy.lower())
    except (ValueError, AttributeError):
        policy_enum = MemoryPolicy.BALANCED

    return AgentConfigData(
        in_a_nutshell=read_section("in_a_nutshell.md"),
        characteristics=read_section("characteristics.md"),
        recent_events=read_section("recent_events.md"),
        profile_pic=find_profile_pic(),
        long_term_memory_index=long_term_memory_index,
        long_term_memory_subtitles=long_term_memory_subtitles,
        memory_brain_enabled=memory_brain_enabled,
        memory_brain_policy=policy_enum,
    )


def list_available_configs() -> Dict[str, Dict[str, Optional[str]]]:
    """
    List all available agent configurations in folder format.

    Supports both direct agent folders and group-based organization:
    - agents/agent_name/ -> ungrouped agent
    - agents/group_체인소맨/agent_name/ -> agent in "체인소맨" group

    Returns:
        Dictionary mapping agent names to config info with keys:
        - "path": str (relative path to agent folder)
        - "group": Optional[str] (group name if in a group folder, None otherwise)
    """
    # Get the project root directory (parent of backend/)
    backend_dir = Path(__file__).parent.parent
    project_root = backend_dir.parent
    agents_dir = project_root / "agents"

    if not agents_dir.exists():
        return {}

    configs = {}
    required_files = ["in_a_nutshell.md", "characteristics.md"]

    # Check for folder-based configs
    for item in agents_dir.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue

        # Check if this is a group folder (starts with "group_")
        if item.name.startswith("group_"):
            # Extract group name (remove "group_" prefix)
            group_name = item.name[6:]  # Remove "group_" prefix

            # Scan for agent folders inside the group folder
            for agent_item in item.iterdir():
                if agent_item.is_dir() and not agent_item.name.startswith("."):
                    # Verify it has at least one required config file
                    if any((agent_item / f).exists() for f in required_files):
                        agent_name = agent_item.name
                        relative_path = agent_item.relative_to(project_root)
                        configs[agent_name] = {"path": str(relative_path), "group": group_name}
        else:
            # Regular agent folder (not in a group)
            if any((item / f).exists() for f in required_files):
                agent_name = item.name
                relative_path = item.relative_to(project_root)
                configs[agent_name] = {"path": str(relative_path), "group": None}

    return configs
