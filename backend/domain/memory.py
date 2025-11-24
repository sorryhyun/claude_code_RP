"""
Memory domain models using Pydantic for structured output.

Contains Pydantic models for memory management, memory brain, and memory state tracking.
Uses Pydantic BaseModel for automatic validation and structured output support.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class MemoryPolicy(str, Enum):
    """Memory selection policies that govern which memories surface."""

    BALANCED = "balanced"  # Neutral, context-driven memory selection
    TRAUMA_BIASED = "trauma_biased"  # Favors painful/difficult memories
    GENIUS_PLANNER = "genius_planner"  # Favors strategic/planning memories
    OPTIMISTIC = "optimistic"  # Favors positive/hopeful memories
    AVOIDANT = "avoidant"  # Suppresses difficult memories


class MemoryEntry(BaseModel):
    """A single long-term memory entry."""

    id: str  # Unique identifier (subtitle from markdown)
    tags: List[str] = Field(default_factory=list)  # Optional tags for categorization
    content_preview: str = ""  # First 100 chars of content for context


class MemoryActivation(BaseModel):
    """Result of memory-brain analysis - represents a single activated memory."""

    memory_id: str
    activation_strength: float = Field(..., ge=0.0, le=1.0, description="Activation strength from 0.0 to 1.0")
    reason: str  # Why this memory was selected


class MemoryBrainOutput(BaseModel):
    """Output from memory-brain analysis using Pydantic structured output."""

    should_inject_now: bool = Field(..., description="Whether to inject memories into the agent's context now")
    activated_memories: List[MemoryActivation] = Field(
        default_factory=list, description="List of activated memories (max 3)"
    )
    reasoning: str = Field(default="", description="Overall reasoning for memory selection decisions")
