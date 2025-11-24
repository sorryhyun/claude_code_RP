import pytest
from domain.task_identifier import TaskIdentifier


def test_task_identifier_str():
    """Test string conversion of TaskIdentifier."""
    task_id = TaskIdentifier(room_id=5, agent_id=3)
    assert str(task_id) == "room_5_agent_3"


def test_task_identifier_pool_key():
    """Test pool_key property returns same as __str__."""
    task_id = TaskIdentifier(room_id=5, agent_id=3)
    assert task_id.pool_key == "room_5_agent_3"
    assert task_id.pool_key == str(task_id)


def test_task_identifier_parse_valid():
    """Test parsing valid task ID string."""
    task_id = TaskIdentifier.parse("room_5_agent_3")
    assert task_id.room_id == 5
    assert task_id.agent_id == 3


def test_task_identifier_parse_invalid_format():
    """Test parsing invalid format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid task ID format"):
        TaskIdentifier.parse("invalid_format")


def test_task_identifier_parse_invalid_format_missing_parts():
    """Test parsing with missing parts raises ValueError."""
    with pytest.raises(ValueError, match="Invalid task ID format"):
        TaskIdentifier.parse("room_5")


def test_task_identifier_parse_invalid_format_wrong_prefix():
    """Test parsing with wrong prefix raises ValueError."""
    with pytest.raises(ValueError, match="Invalid task ID format"):
        TaskIdentifier.parse("foo_5_agent_3")


def test_task_identifier_parse_invalid_format_wrong_middle():
    """Test parsing with wrong middle word raises ValueError."""
    with pytest.raises(ValueError, match="Invalid task ID format"):
        TaskIdentifier.parse("room_5_foo_3")


def test_task_identifier_parse_invalid_numbers():
    """Test parsing with invalid numeric IDs raises ValueError."""
    with pytest.raises(ValueError, match="Invalid numeric IDs in task ID"):
        TaskIdentifier.parse("room_abc_agent_def")


def test_task_identifier_parse_invalid_room_number():
    """Test parsing with invalid room number raises ValueError."""
    with pytest.raises(ValueError, match="Invalid numeric IDs in task ID"):
        TaskIdentifier.parse("room_abc_agent_3")


def test_task_identifier_parse_invalid_agent_number():
    """Test parsing with invalid agent number raises ValueError."""
    with pytest.raises(ValueError, match="Invalid numeric IDs in task ID"):
        TaskIdentifier.parse("room_5_agent_def")


def test_task_identifier_equality():
    """Test TaskIdentifier equality."""
    task1 = TaskIdentifier(room_id=1, agent_id=2)
    task2 = TaskIdentifier(room_id=1, agent_id=2)
    task3 = TaskIdentifier(room_id=1, agent_id=3)
    assert task1 == task2
    assert task1 != task3


def test_task_identifier_hashable():
    """Test TaskIdentifier can be used as dict key."""
    task_id = TaskIdentifier(room_id=1, agent_id=2)
    task_dict = {task_id: "value"}
    assert task_dict[task_id] == "value"


def test_task_identifier_hashable_equality():
    """Test equal TaskIdentifiers have same hash."""
    task1 = TaskIdentifier(room_id=1, agent_id=2)
    task2 = TaskIdentifier(room_id=1, agent_id=2)
    assert hash(task1) == hash(task2)


def test_task_identifier_frozen():
    """Test TaskIdentifier is immutable."""
    task_id = TaskIdentifier(room_id=1, agent_id=2)
    with pytest.raises(AttributeError):
        task_id.room_id = 3


def test_task_identifier_round_trip():
    """Test parse and str are inverse operations."""
    original = "room_42_agent_7"
    task_id = TaskIdentifier.parse(original)
    assert str(task_id) == original


def test_task_identifier_different_ids():
    """Test TaskIdentifier with different IDs."""
    task1 = TaskIdentifier(room_id=1, agent_id=1)
    task2 = TaskIdentifier(room_id=1, agent_id=2)
    task3 = TaskIdentifier(room_id=2, agent_id=1)
    task4 = TaskIdentifier(room_id=2, agent_id=2)

    assert task1 != task2
    assert task1 != task3
    assert task1 != task4
    assert task2 != task3
    assert task2 != task4
    assert task3 != task4


def test_task_identifier_use_in_set():
    """Test TaskIdentifier can be used in sets."""
    task1 = TaskIdentifier(room_id=1, agent_id=2)
    task2 = TaskIdentifier(room_id=1, agent_id=2)  # Same as task1
    task3 = TaskIdentifier(room_id=1, agent_id=3)

    task_set = {task1, task2, task3}
    assert len(task_set) == 2  # task1 and task2 are the same
    assert task1 in task_set
    assert task3 in task_set
