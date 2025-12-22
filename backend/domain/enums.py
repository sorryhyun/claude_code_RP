"""
Domain enums for type-safe constants.
"""

from enum import Enum


class ParticipantType(str, Enum):
    """Type of participant in a chat message."""

    USER = "user"
    CHARACTER = "character"
    SITUATION_BUILDER = "situation_builder"
    SYSTEM = "system"
    AGENT = "agent"  # For backwards compatibility with evaluation scripts

    def __str__(self) -> str:
        return self.value
