from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class TaskIdentifier:
    """Structured identifier for agent tasks.

    Replaces fragile string parsing of 'room_X_agent_Y' format.
    """

    room_id: int
    agent_id: int

    def __str__(self) -> str:
        """Generate pool key for client pooling."""
        return f"room_{self.room_id}_agent_{self.agent_id}"

    @classmethod
    def parse(cls, task_id_str: str) -> Self:
        """Parse task ID string with validation.

        Args:
            task_id_str: Format 'room_{room_id}_agent_{agent_id}'

        Returns:
            TaskIdentifier instance

        Raises:
            ValueError: If format is invalid
        """
        parts = task_id_str.split("_")
        if len(parts) != 4 or parts[0] != "room" or parts[2] != "agent":
            raise ValueError(f"Invalid task ID format: {task_id_str}")

        try:
            room_id = int(parts[1])
            agent_id = int(parts[3])
        except ValueError as e:
            raise ValueError(f"Invalid numeric IDs in task ID: {task_id_str}") from e

        return cls(room_id=room_id, agent_id=agent_id)

    @property
    def pool_key(self) -> str:
        """Alias for __str__() for clarity in client pooling."""
        return str(self)
