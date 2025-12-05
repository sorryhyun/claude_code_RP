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
