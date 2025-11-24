"""
Memory Brain - A separate agent that decides which long-term memories should surface.

The memory-brain receives the character's profile, scene summary, and available memories,
then decides which memories naturally "surface" for this moment using configurable policies.

ARCHITECTURE DECISION: Simple Activation Tracking
==================================================
This module uses a simple set-based activation tracking approach (_activated_memories).
An alternative implementation (memory_state.py with MemoryStateTracker) was removed in
Phase 1 refactoring due to:
1. Unused functionality - tracking was maintained but never consulted
2. Over-engineering - cooldown mechanism not yet required
3. Duplication - two parallel tracking systems for same purpose

Current approach (Option A - Simple Set-Based):
- Lightweight tracking per room
- Infrastructure ready for future cooldown mechanism
- Memory brain agent already avoids redundancy via conversation context

Alternative approach (Option B - Full History, removed):
- MemoryStateTracker with cooldown periods
- Full activation history per memory
- More complex but unused features

If cooldown functionality is needed in the future, it can be added incrementally to
the existing _activated_memories infrastructure without reintroducing the full
MemoryStateTracker complexity.
"""

import logging
from typing import Dict, List, Optional

from domain.memory import MemoryBrainOutput, MemoryEntry, MemoryPolicy
from sdk.memory_brain_manager import MemoryBrainSDKManager

logger = logging.getLogger("MemoryBrain")


class MemoryBrain:
    """
    Stateless agent that decides which memories naturally surface.

    On each turn, analyzes:
    - Character's core identity (in_a_nutshell)
    - Current scene context (recent messages)
    - Available long-term memories
    - Recently activated memories (to avoid repeats)
    - Policy configuration

    Returns:
    - Which memories should surface (0-3)
    - Activation strength per memory (0.0-1.0)
    - Whether to inject memories into the next prompt
    """

    def __init__(self, max_memories: int = 3):
        """
        Initialize memory brain.

        Args:
            max_memories: Maximum number of memories to surface per turn (default: 3)
        """
        self.max_memories = max_memories
        self._sdk_manager = MemoryBrainSDKManager(max_memories=max_memories)

        # NOTE: Activation tracking is currently for infrastructure/debugging only.
        # This state is maintained but not actively consulted in memory selection.
        #
        # Future enhancement: Implement cooldown mechanism to prevent re-surfacing
        # the same memories within N turns. The memory brain agent already avoids
        # redundancy by seeing conversation context, but explicit cooldowns could
        # provide additional control.
        #
        # Design considerations:
        # - Should cooldowns be per-room or global per agent?
        # - How many turns before a memory can resurface? (e.g., 10 turns)
        # - Should cooldown duration vary by memory importance/activation strength?
        #
        # Track which memories have been activated per room (to avoid repeats)
        self._activated_memories: Dict[int, set[str]] = {}  # room_id -> set of memory_ids

    def increment_turn(self, room_id: int):
        """
        Initialize tracking for a room if not exists.
        Called when user sends a message to start tracking for that conversation.

        Args:
            room_id: Room ID to initialize tracking for
        """
        if room_id not in self._activated_memories:
            self._activated_memories[room_id] = set()

    def get_activated_memories(self, room_id: int) -> set[str]:
        """
        Get the set of already-activated memory IDs for this room.

        Args:
            room_id: Room ID to get activated memories for

        Returns:
            Set of memory IDs that have been activated in this room
        """
        return self._activated_memories.get(room_id, set())

    def record_activated_memories(self, room_id: int, memory_ids: List[str]):
        """
        Record that these memories were activated in this room.

        Args:
            room_id: Room ID to record for
            memory_ids: List of memory IDs that were activated
        """
        if room_id not in self._activated_memories:
            self._activated_memories[room_id] = set()
        self._activated_memories[room_id].update(memory_ids)
        logger.debug(
            f"Recorded {len(memory_ids)} activated memories for room {room_id}. Total: {len(self._activated_memories[room_id])}"
        )

    async def analyze(
        self,
        conversation_context: str,
        available_memories: List[MemoryEntry],
        policy: MemoryPolicy = MemoryPolicy.BALANCED,
        agent_name: str = "",
        in_a_nutshell: str = "",
        characteristics: str = "",
        agent_count: Optional[int] = None,
        user_name: Optional[str] = None,
        has_situation_builder: bool = False,
    ) -> MemoryBrainOutput:
        """
        Analyze context and determine which memories should surface.

        The memory brain will naturally avoid redundancy by seeing which memories
        are already reflected in the conversation context.

        Args:
            conversation_context: Full conversation context that the agent sees
            available_memories: List of available long-term memory entries
            policy: Memory selection policy to use
            agent_name: Name of the agent
            in_a_nutshell: Agent's brief identity summary
            characteristics: Agent's personality traits
            agent_count: Number of agents in the room (for detecting 1-on-1 conversations)
            user_name: Name of the user/character participant (for 1-on-1 conversations)
            has_situation_builder: Whether conversation includes situation_builder messages

        Returns:
            MemoryBrainOutput with selected memories and injection flag
        """
        # Delegate to SDK manager
        return await self._sdk_manager.analyze_memories(
            conversation_context=conversation_context,
            available_memories=available_memories,
            policy=policy,
            agent_name=agent_name,
            in_a_nutshell=in_a_nutshell,
            characteristics=characteristics,
            agent_count=agent_count,
            user_name=user_name,
            has_situation_builder=has_situation_builder,
        )

    def cleanup(self, room_id: int):
        """
        Clear memory state for a specific room.

        Args:
            room_id: Room ID to clear state for
        """
        if room_id in self._activated_memories:
            del self._activated_memories[room_id]
            logger.debug(f"Cleared activated memories for room {room_id}")

    async def cleanup_all(self):
        """Clean up all resources and disconnect SDK client."""
        await self._sdk_manager.cleanup()
        self._activated_memories.clear()
