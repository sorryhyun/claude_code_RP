"""FastAPI routers for modular endpoint organization."""

from . import agent_management, agents, auth, debug, mcp_tools, messages, room_agents, rooms

__all__ = [
    "auth",
    "rooms",
    "agents",
    "room_agents",
    "messages",
    "agent_management",
    "debug",
    "mcp_tools",
]
