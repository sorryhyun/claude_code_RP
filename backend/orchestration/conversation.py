"""
Shared utilities for conversation context analysis.

Provides common functions for detecting conversation types and participants
used across orchestration and SDK layers.
"""

from typing import List, Optional, Tuple

from core import get_settings

# Get settings singleton
_settings = get_settings()


def detect_conversation_type(messages: List, agent_count: int) -> Tuple[bool, Optional[str], bool]:
    """
    Analyze messages to detect conversation type and participants.

    Args:
        messages: List of message objects (must have .role, .participant_type, .participant_name)
        agent_count: Number of agents in the room

    Returns:
        Tuple of (is_one_on_one, user_name, has_situation_builder):
            - is_one_on_one: True if this is a 1-on-1 conversation between agent and user/character
            - user_name: Name of the user/character participant (None if not found or not 1-on-1)
            - has_situation_builder: True if conversation includes situation_builder messages
    """
    user_name = None
    has_user_or_character = False
    has_situation_builder = False

    for msg in messages:
        if msg.role == "user":
            if msg.participant_type == "situation_builder":
                has_situation_builder = True
            elif msg.participant_type == "character" and msg.participant_name:
                has_user_or_character = True
                if user_name is None:  # Take the first one found
                    user_name = msg.participant_name
            elif msg.participant_type == "user":
                has_user_or_character = True
                if user_name is None:
                    user_name = _settings.user_name

    # It's a 1-on-1 conversation if:
    # - Only 1 agent in the room
    # - At least one user/character message exists
    # - No situation_builder messages
    is_one_on_one = agent_count == 1 and has_user_or_character and not has_situation_builder

    return is_one_on_one, user_name, has_situation_builder


def get_user_name_from_messages(messages: List) -> Optional[str]:
    """
    Extract user/character name from messages.

    Priority:
    1. Character participant name
    2. USER_NAME from environment or "User"

    Args:
        messages: List of message objects

    Returns:
        User/character name or None if no user messages found
    """
    for msg in messages:
        if msg.role == "user":
            if msg.participant_type == "character" and msg.participant_name:
                return msg.participant_name
            elif msg.participant_type == "user":
                return _settings.user_name

    return None
