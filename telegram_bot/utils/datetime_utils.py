"""
UTC-first datetime utilities for Telegram bot.

This module provides consistent datetime handling across the bot:
- All timestamps are in UTC for consistency with backend
- Human-friendly formatting for Telegram messages
- Timezone-aware parsing and conversion

Design Choices:
- UTC everywhere - matches backend datetime handling
- Human-readable output with clear "UTC" indicator
- Simple functions - no external dependencies beyond stdlib

Usage:
    from utils.datetime_utils import utc_now, format_for_user, format_for_api
    
    # Get current time
    now = utc_now()
    
    # Format for display in Telegram message
    display_str = format_for_user(now)  # "29 Dec 2024, 14:30 UTC"
    
    # Format for API call
    api_str = format_for_api(now)  # "2024-12-29T14:30:00Z"
"""

from datetime import datetime, timezone
from typing import Union, Optional


def utc_now() -> datetime:
    """
    Get current datetime in UTC with timezone info.
    
    Returns:
        datetime: Current time as timezone-aware datetime in UTC.
    
    Example:
        >>> now = utc_now()
        >>> print(format_for_user(now))
        "29 Dec 2024, 14:30 UTC"
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.
    
    - If datetime is naive (no timezone), assumes it's already UTC
    - If datetime has timezone, converts to UTC
    
    Args:
        dt: A datetime object (naive or timezone-aware).
    
    Returns:
        datetime: Timezone-aware datetime in UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_for_user(
    dt: Union[datetime, str],
    include_time: bool = True,
    include_seconds: bool = False
) -> str:
    """
    Format datetime for display in Telegram messages.
    
    Produces human-readable output with explicit UTC indicator.
    Users worldwide see the same time reference.
    
    Args:
        dt: Datetime object or ISO string to format.
        include_time: Whether to include time portion.
        include_seconds: Whether to include seconds (if include_time is True).
    
    Returns:
        str: Human-readable datetime string like "29 Dec 2024, 14:30 UTC"
    
    Examples:
        >>> format_for_user(datetime(2024, 12, 29, 14, 30, tzinfo=timezone.utc))
        '29 Dec 2024, 14:30 UTC'
        
        >>> format_for_user(datetime(2024, 12, 29, 14, 30, 45, tzinfo=timezone.utc), include_seconds=True)
        '29 Dec 2024, 14:30:45 UTC'
        
        >>> format_for_user(datetime(2024, 12, 29, tzinfo=timezone.utc), include_time=False)
        '29 Dec 2024'
    """
    # Parse string to datetime if needed
    if isinstance(dt, str):
        dt = parse_iso(dt)
    
    # Ensure UTC
    dt = to_utc(dt)
    
    if include_time:
        if include_seconds:
            return dt.strftime("%d %b %Y, %H:%M:%S UTC")
        return dt.strftime("%d %b %Y, %H:%M UTC")
    return dt.strftime("%d %b %Y")


def format_for_api(dt: datetime) -> str:
    """
    Format datetime for API calls (ISO 8601 with Z suffix).
    
    This format is compatible with the Health Service API.
    
    Args:
        dt: Datetime to format.
    
    Returns:
        str: ISO 8601 formatted string like "2024-12-29T14:30:00Z"
    """
    utc_dt = to_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    """
    Parse an ISO 8601 datetime string to UTC datetime.
    
    Args:
        value: ISO format datetime string.
    
    Returns:
        datetime: Timezone-aware datetime in UTC.
    
    Raises:
        ValueError: If the string cannot be parsed.
    """
    value = value.strip()
    
    # Handle 'Z' suffix (UTC indicator)
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    
    dt = datetime.fromisoformat(value)
    return to_utc(dt)


def parse_iso_safe(value: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO datetime string with graceful error handling.
    
    Args:
        value: ISO format datetime string, or None.
    
    Returns:
        Parsed datetime in UTC, or None if parsing fails.
    """
    if not value:
        return None
    try:
        return parse_iso(value)
    except (ValueError, AttributeError):
        return None


def format_relative(dt: datetime) -> str:
    """
    Format datetime as a relative time string.
    
    Useful for showing how long ago something happened.
    
    Args:
        dt: Datetime to format (should be in the past).
    
    Returns:
        str: Relative time like "2 hours ago", "just now", "3 days ago"
    """
    now = utc_now()
    dt = to_utc(dt)
    delta = now - dt
    
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

