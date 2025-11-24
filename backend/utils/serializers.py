"""
Serialization helper functions for Pydantic models.
"""

from datetime import datetime, timezone


def serialize_utc_datetime(dt: datetime) -> datetime:
    """
    Convert naive UTC datetime to timezone-aware before serialization.

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Timezone-aware datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def serialize_sqlite_bool(value: int) -> bool:
    """
    Convert SQLite integer (0/1) to boolean.

    Args:
        value: Integer value (0 or 1)

    Returns:
        Boolean value
    """
    return bool(value)
