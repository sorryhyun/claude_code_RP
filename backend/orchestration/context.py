"""
Conversation context builder for multi-agent chat rooms.

This module provides functionality to build conversation context from
recent room messages for multi-agent awareness.
"""

from typing import List, Optional

from config.config_loader import get_conversation_context_config
from config.constants import SKIP_MESSAGE_TEXT
from config.parser import GUIDELINE_READ_MODE, MEMORY_MODE
from core import get_settings
from utils.conversation_utils import detect_conversation_type
from utils.korean_particles import format_with_particles


def build_conversation_context(
    messages: List,
    limit: int = 25,
    agent_id: Optional[int] = None,
    agent_name: Optional[str] = None,
    agent_count: Optional[int] = None,
    user_name: Optional[str] = None,
    include_response_instruction: bool = True,
) -> str:
    """
    Build conversation context from recent room messages for multi-agent awareness.

    Args:
        messages: List of recent messages from the room
        limit: Maximum number of recent messages to include
        agent_id: If provided, only include messages after this agent's last response
        agent_name: Optional agent name to include in the thinking block instruction
        agent_count: Number of agents in the room (for detecting 1-on-1 conversations)
        user_name: Name of the user/character participant (for 1-on-1 conversations)
        include_response_instruction: If True, append response instruction; if False, only include conversation history

    Returns:
        Formatted conversation history string
    """
    if not messages:
        return ""

    # If agent_id is provided, find messages after the agent's last response
    if agent_id is not None:
        # Find the index of the agent's last message
        last_agent_msg_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].agent_id == agent_id:
                last_agent_msg_idx = i
                break

        # If agent has responded before, only include messages after that
        if last_agent_msg_idx >= 0:
            recent_messages = messages[last_agent_msg_idx + 1 :]
        else:
            # Agent hasn't responded yet, use recent messages
            recent_messages = messages[-limit:] if len(messages) > limit else messages
    else:
        # No agent_id provided, use recent messages
        recent_messages = messages[-limit:] if len(messages) > limit else messages

    # If no new messages, return empty
    if not recent_messages:
        return ""

    # Load conversation context configuration
    context_config = get_conversation_context_config()
    config = context_config.get("conversation_context", {})

    # Build header
    header = config.get("header", "Here's the conversation so far:")
    context_lines = [header]

    # Track seen messages to avoid duplicates (speaker, content) pairs
    seen_messages = set()

    for msg in recent_messages:
        # Skip messages that are marked as "skip" (invisible to others)
        # Also handle legacy Korean text for backward compatibility
        if msg.content == SKIP_MESSAGE_TEXT or msg.content == "(무시함)":
            continue

        # Skip system messages (e.g., "X joined the chat") - these are UI-only notifications
        if msg.participant_type == "system":
            continue

        # Format each message with speaker identification
        if msg.role == "user":
            # Determine speaker based on participant type
            if msg.participant_type == "character" and msg.participant_name:
                speaker = msg.participant_name
            elif msg.participant_type == "situation_builder":
                speaker = "Situation Builder"
            else:
                # Default to USER_NAME or "User"
                speaker = get_settings().user_name
        elif msg.agent_id:
            # Get agent name from the message relationship
            speaker = msg.agent.name if hasattr(msg, "agent") and msg.agent else f"Agent {msg.agent_id}"
        else:
            speaker = "Unknown"

        # Create a unique key for this message (speaker + content)
        message_key = (speaker, msg.content)

        # Skip if we've already seen this exact message from this speaker
        if message_key in seen_messages:
            continue

        seen_messages.add(message_key)
        context_lines.append(f"{speaker}: {msg.content}\n")

    # Add footer (closing tag) after conversation messages
    footer = config.get("footer", "")
    if footer:
        context_lines.append(footer)

    # Add recall tool reminder (only in RECALL mode and when including instructions)
    if include_response_instruction and MEMORY_MODE == "RECALL":
        recall_reminder = config.get("recall_reminder", "")
        if recall_reminder:
            context_lines.append(f"\n{recall_reminder}\n")

    # Add response instruction based on conversation type (if requested)
    if include_response_instruction:
        # Determine conversation type using shared utility
        is_one_on_one, _, _ = detect_conversation_type(recent_messages, agent_count or 0)

        # Add response instruction based on conversation type
        # Use _active variants when READ_GUIDELINE_BY=active_tool
        if agent_name:
            # Use 1-on-1 template if it's a 1-on-1 conversation and user_name is provided
            if is_one_on_one and user_name:
                if GUIDELINE_READ_MODE == "active_tool":
                    instruction = config.get("response_instruction_with_user_active", "")
                    # Fallback to regular instruction if _active variant not found
                    if not instruction:
                        instruction = config.get("response_instruction_with_user", "")
                else:
                    instruction = config.get("response_instruction_with_user", "")
                if instruction:
                    context_lines.append(format_with_particles(instruction, agent_name=agent_name, user_name=user_name))
            else:
                # Use multi-agent template when there are multiple agents (>1)
                # Otherwise use standard agent template
                if agent_count and agent_count > 1:
                    if GUIDELINE_READ_MODE == "active_tool":
                        instruction = config.get("response_instruction_with_multi_agent_active", "")
                        # Fallback to regular agent instruction if multi_agent variant not found
                        if not instruction:
                            instruction = config.get("response_instruction_with_agent_active", "")
                        if not instruction:
                            instruction = config.get("response_instruction_with_agent", "")
                    else:
                        instruction = config.get("response_instruction_with_multi_agent", "")
                        # Fallback to regular agent instruction if multi_agent variant not found
                        if not instruction:
                            instruction = config.get("response_instruction_with_agent", "")
                else:
                    # Standard agent template for situation_builder or single agent scenarios
                    if GUIDELINE_READ_MODE == "active_tool":
                        instruction = config.get("response_instruction_with_agent_active", "")
                        # Fallback to regular instruction if _active variant not found
                        if not instruction:
                            instruction = config.get("response_instruction_with_agent", "")
                    else:
                        instruction = config.get("response_instruction_with_agent", "")
                if instruction:
                    context_lines.append(format_with_particles(instruction, agent_name=agent_name))
        else:
            instruction = config.get("response_instruction_default", "")
            if instruction:
                context_lines.append(instruction)

    return "\n".join(context_lines)
