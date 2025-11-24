"""
General helper functions for the ChitChats backend.
"""

from domain.task_identifier import TaskIdentifier


def get_pool_key(room_id: int, agent_id: int) -> TaskIdentifier:
    """
    Generate a consistent pool key for room-agent pairs.
    Used for agent client pooling and task tracking.

    Args:
        room_id: Room ID
        agent_id: Agent ID

    Returns:
        TaskIdentifier instance for this room-agent pair
    """
    return TaskIdentifier(room_id=room_id, agent_id=agent_id)
