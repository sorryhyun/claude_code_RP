"""
Timezone utilities for converting between UTC and KST (Korean Standard Time).
"""

from datetime import datetime, timedelta, timezone

# KST is UTC+9
KST = timezone(timedelta(hours=9))


def utc_to_kst(dt: datetime) -> datetime:
    """
    Convert a UTC datetime to KST (Korean Standard Time).

    Args:
        dt: Datetime object in UTC (naive or timezone-aware)

    Returns:
        Timezone-aware datetime in KST
    """
    if dt is None:
        return None

    # If naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to KST
    return dt.astimezone(KST)


def make_timezone_aware(dt: datetime) -> datetime:
    """
    Convert a naive UTC datetime to timezone-aware datetime.
    If already timezone-aware, returns as-is.

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Timezone-aware datetime
    """
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def format_kst_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime as KST string.

    Args:
        dt: Datetime object in any timezone (will be converted to KST)
        format_str: strftime format string

    Returns:
        Formatted timestamp string in KST
    """
    if dt is None:
        return ""

    kst_dt = utc_to_kst(dt)
    return kst_dt.strftime(format_str)
