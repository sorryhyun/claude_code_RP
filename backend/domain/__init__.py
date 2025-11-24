"""
Domain layer for internal business logic data structures.

This package contains dataclasses used for clean parameter passing
between functions in the business logic layer.
"""

from .action_models import (
    MemorizeInput,
    MemorizeOutput,
    RecallInput,
    RecallOutput,
    SkipInput,
    SkipOutput,
    ToolResponse,
)
from .agent_config import AgentConfigData
from .contexts import (
    AgentMessageData,
    AgentResponseContext,
    MessageContext,
    OrchestrationContext,
)

__all__ = [
    "AgentConfigData",
    "AgentResponseContext",
    "OrchestrationContext",
    "MessageContext",
    "AgentMessageData",
    "SkipInput",
    "SkipOutput",
    "MemorizeInput",
    "MemorizeOutput",
    "RecallInput",
    "RecallOutput",
    "ToolResponse",
]
