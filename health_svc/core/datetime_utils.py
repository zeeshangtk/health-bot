"""
UTC-first datetime utilities for Health Service API.

This module provides consistent datetime handling across the application:
- All datetimes are stored and processed in UTC
- ISO 8601 format used for string serialization
- Timezone-aware parsing and conversion

Design Principles:
- Internal processing: Always use datetime with UTC timezone
- Database storage: ISO 8601 strings in UTC (SQLite stores as TEXT)
- API responses: ISO 8601 strings with 'Z' suffix
- API requests: Accept various ISO 8601 formats, normalize to UTC

Usage:
    from core.datetime_utils import utc_now, to_utc, parse_datetime, format_iso
    
    # Get current UTC time
    now = utc_now()
    
    # Parse incoming datetime string to UTC
    dt = parse_datetime("2024-01-15T10:30:00+05:30")  # Converts to UTC
    
    # Format for storage/response
    iso_str = format_iso(dt)  # "2024-01-15T05:00:00Z"
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Union

logger = logging.getLogger(__name__)


# =============================================================================
# CORE UTILITIES
# =============================================================================

def utc_now() -> datetime:
    """
    Get current datetime in UTC with timezone info.
    
    Returns:
        datetime: Current time as timezone-aware datetime in UTC.
    
    Example:
        >>> now = utc_now()
        >>> now.tzinfo
        datetime.timezone.utc
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
    
    Example:
        >>> from datetime import timezone, timedelta
        >>> ist = timezone(timedelta(hours=5, minutes=30))
        >>> dt_ist = datetime(2024, 1, 15, 16, 0, tzinfo=ist)
        >>> dt_utc = to_utc(dt_ist)
        >>> dt_utc.hour
        10
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return dt.astimezone(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is UTC, handling None gracefully.
    
    Args:
        dt: Optional datetime object.
    
    Returns:
        Optional datetime in UTC, or None if input is None.
    """
    return to_utc(dt) if dt is not None else None


# =============================================================================
# PARSING
# =============================================================================

def parse_datetime(value: Union[str, datetime]) -> datetime:
    """
    Parse a datetime value to UTC datetime.
    
    Accepts:
    - datetime object (returned as-is after UTC conversion)
    - ISO 8601 string (with or without timezone)
    - Common date formats
    
    Args:
        value: DateTime string or object to parse.
    
    Returns:
        datetime: Timezone-aware datetime in UTC.
    
    Raises:
        ValueError: If the value cannot be parsed.
    
    Examples:
        >>> parse_datetime("2024-01-15T10:30:00Z")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        
        >>> parse_datetime("2024-01-15T10:30:00+05:30")  # Converts to UTC
        datetime.datetime(2024, 1, 15, 5, 0, tzinfo=datetime.timezone.utc)
    """
    if isinstance(value, datetime):
        return to_utc(value)
    
    if not isinstance(value, str):
        raise ValueError(f"Expected datetime or string, got {type(value).__name__}")
    
    value = value.strip()
    
    # Try ISO format first (most common)
    try:
        # Handle 'Z' suffix (UTC indicator)
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        return to_utc(dt)
    except ValueError:
        pass
    
    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",      # 2024-01-15 10:30:00
        "%Y-%m-%d %H:%M",         # 2024-01-15 10:30
        "%Y-%m-%d",               # 2024-01-15
        "%d-%m-%Y %H:%M:%S",      # 15-01-2024 10:30:00
        "%d-%m-%Y %H:%M",         # 15-01-2024 10:30
        "%d-%m-%Y",               # 15-01-2024
        "%d/%m/%Y %H:%M:%S",      # 15/01/2024 10:30:00
        "%d/%m/%Y %H:%M",         # 15/01/2024 10:30
        "%d/%m/%Y",               # 15/01/2024
        "%d-%m-%Y %I:%M %p",      # 15-01-2024 10:30 AM (lab report format)
        "%d/%m/%Y %I:%M %p",      # 15/01/2024 10:30 AM
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            # Naive datetime from strptime - assume UTC
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    
    raise ValueError(f"Cannot parse datetime: '{value}'")


def parse_datetime_safe(value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse datetime with graceful error handling.
    
    Args:
        value: DateTime value to parse, or None.
    
    Returns:
        Parsed datetime in UTC, or None if parsing fails or input is None.
    """
    if value is None:
        return None
    try:
        return parse_datetime(value)
    except ValueError as e:
        logger.warning(f"Failed to parse datetime '{value}': {e}")
        return None


# =============================================================================
# FORMATTING
# =============================================================================

def format_iso(dt: datetime) -> str:
    """
    Format datetime to ISO 8601 string with UTC timezone.
    
    Args:
        dt: Datetime to format.
    
    Returns:
        str: ISO 8601 formatted string with 'Z' suffix for UTC.
    
    Example:
        >>> format_iso(datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc))
        '2024-01-15T10:30:00Z'
    """
    utc_dt = to_utc(dt)
    # Use 'Z' suffix instead of '+00:00' for cleaner output
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_iso_with_offset(dt: datetime) -> str:
    """
    Format datetime to ISO 8601 string with explicit offset.
    
    Args:
        dt: Datetime to format.
    
    Returns:
        str: ISO 8601 formatted string with timezone offset.
    
    Example:
        >>> format_iso_with_offset(datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc))
        '2024-01-15T10:30:00+00:00'
    """
    utc_dt = to_utc(dt)
    return utc_dt.isoformat()


def format_for_display(dt: datetime, include_time: bool = True) -> str:
    """
    Format datetime for human-readable display.
    
    Args:
        dt: Datetime to format.
        include_time: Whether to include time portion.
    
    Returns:
        str: Human-readable datetime string.
    
    Example:
        >>> format_for_display(datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc))
        '15 Jan 2024, 10:30 UTC'
    """
    utc_dt = to_utc(dt)
    if include_time:
        return utc_dt.strftime("%d %b %Y, %H:%M UTC")
    return utc_dt.strftime("%d %b %Y")


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def to_db_string(dt: datetime) -> str:
    """
    Convert datetime to string format for SQLite storage.
    
    SQLite stores datetimes as TEXT. We use ISO 8601 format for consistency.
    
    Args:
        dt: Datetime to convert.
    
    Returns:
        str: ISO 8601 formatted string for database storage.
    """
    return format_iso(dt)


def from_db_string(value: Optional[str]) -> Optional[datetime]:
    """
    Parse datetime string from SQLite storage.
    
    Args:
        value: String from database, or None.
    
    Returns:
        Parsed datetime in UTC, or None if value is None or invalid.
    """
    return parse_datetime_safe(value)


