"""
Centralized path utilities for handling both development and PyInstaller frozen modes.

In frozen (exe) mode:
- get_base_path(): Returns PyInstaller temp extraction dir (_MEIPASS) for bundled resources
- get_work_dir(): Returns exe parent directory for user data (agents, .env, database)

In development mode:
- Both return the project root (parent of backend/)
"""

import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the base path for bundled resources.

    In frozen mode: Returns _MEIPASS (PyInstaller temp extraction directory)
    In dev mode: Returns project root (parent of backend/)

    Use this for resources bundled inside the exe (static files, templates).
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    else:
        # backend/core/paths.py -> backend/core -> backend -> project_root
        return Path(__file__).parent.parent.parent


def get_work_dir() -> Path:
    """
    Get the working directory for user data.

    In frozen mode: Returns the directory containing the exe
    In dev mode: Returns project root (parent of backend/)

    Use this for user-modifiable data: agents/, .env, database, etc.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        # backend/core/paths.py -> backend/core -> backend -> project_root
        return Path(__file__).parent.parent.parent


def get_agents_dir() -> Path:
    """Get the agents directory."""
    return get_work_dir() / "agents"


def get_config_dir() -> Path:
    """Get the config directory for YAML files."""
    return get_base_path() / "backend" / "config"
