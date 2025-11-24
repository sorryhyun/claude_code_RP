"""
Message handlers for broadcasting and saving chat messages.

This module provides helper functions for broadcasting typing indicators,
saving/broadcasting agent messages, and handling streaming responses.

ARCHITECTURE NOTE: Polling vs. Real-time Broadcasting
======================================================
Most broadcast functions are no-ops because ChitChats uses HTTP polling architecture:
- Clients poll /api/rooms/{room_id}/messages every 2 seconds
- No WebSocket or SSE connections for real-time updates
- Broadcast functions are kept for backward compatibility and semantic clarity

Active functions:
- broadcast_stream_end: Saves complete messages to database
- save_and_broadcast_agent_message: Saves messages to database

No-op functions (kept for API compatibility):
- broadcast_typing_indicator: Would show "agent is typing" in real-time systems
- broadcast_stream_start: Would notify clients of streaming start
- broadcast_stream_delta: Would stream partial message updates

These no-ops could be removed in a future refactor, but are retained to:
1. Maintain clear semantic meaning in calling code
2. Allow easy migration to real-time architecture if needed
3. Avoid breaking changes to response_generator.py and orchestrator.py
"""

import logging

import crud
import schemas
from domain.contexts import AgentMessageData, MessageContext

logger = logging.getLogger("MessageHandlers")


async def broadcast_typing_indicator(context: MessageContext):
    """Broadcast typing indicator for an agent (no-op for polling architecture).

    Args:
        context: MessageContext containing broadcast parameters
    """
    # No-op: Polling architecture doesn't use real-time broadcasting
    pass


async def save_and_broadcast_agent_message(
    context: MessageContext, message_data: AgentMessageData, broadcast: bool = True
):
    """Save agent message to database (polling architecture).

    Args:
        context: MessageContext containing db, room, and agent
        message_data: AgentMessageData containing message content and thinking
        broadcast: Unused parameter kept for backward compatibility
    """
    # Save agent message
    agent_message = schemas.MessageCreate(
        content=message_data.content,
        role="assistant",
        agent_id=context.agent.id,
        thinking=message_data.thinking if message_data.thinking else None,
    )
    # Update room activity for agent messages so unread notifications appear
    saved_agent_msg = await crud.create_message(context.db, context.room_id, agent_message, update_room_activity=True)

    # No broadcast: Polling architecture - clients poll for new messages


async def broadcast_stream_start(context: MessageContext, temp_id: str):
    """Broadcast stream start event (no-op for polling architecture).

    Args:
        context: MessageContext containing room and agent info
        temp_id: Temporary ID for the streaming message
    """
    # No-op: Polling architecture doesn't use real-time streaming
    pass


async def broadcast_stream_delta(
    context: MessageContext, temp_id: str, content_delta: str = "", thinking_delta: str = ""
):
    """Broadcast a streaming delta (no-op for polling architecture).

    Args:
        context: MessageContext containing room info
        temp_id: Temporary ID for the streaming message
        content_delta: Text content delta to append
        thinking_delta: Thinking text delta to append
    """
    # No-op: Polling architecture doesn't use real-time streaming
    pass


async def broadcast_stream_end(
    context: MessageContext, temp_id: str, message_data: AgentMessageData, broadcast: bool = True
):
    """Save complete message to database (polling architecture).

    Args:
        context: MessageContext containing db, room, and agent
        temp_id: Temporary ID for the streaming message (unused in polling architecture)
        message_data: AgentMessageData containing complete message content and thinking
        broadcast: Unused parameter kept for backward compatibility

    Returns:
        The saved message database ID
    """
    # Save agent message to database
    agent_message = schemas.MessageCreate(
        content=message_data.content,
        role="assistant",
        agent_id=context.agent.id,
        thinking=message_data.thinking if message_data.thinking else None,
    )
    # Update room activity for agent messages so unread notifications appear
    saved_agent_msg = await crud.create_message(context.db, context.room_id, agent_message, update_room_activity=True)

    # No broadcast: Polling architecture - clients poll for new messages

    return saved_agent_msg.id
