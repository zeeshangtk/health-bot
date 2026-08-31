"""
Shared date-parsing helpers for lab report data.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_sample_date(date_str: str) -> datetime:
    """
    Parse sample date string from lab report format to datetime.

    Expected format: "DD-MM-YYYY HH:MM AM/PM"
    Example: "08-11-2025 03:17 PM"

    Args:
        date_str: Date string in format "DD-MM-YYYY HH:MM AM/PM".

    Returns:
        datetime: Parsed datetime object.

    Raises:
        ValueError: If date string cannot be parsed.
    """
    formats = [
        "%d-%m-%Y %I:%M %p",  # 08-11-2025 03:17 PM
        "%d/%m/%Y %I:%M %p",  # 28/09/2025 03:17 PM
        "%d-%m-%Y %H:%M %p",  # 28-09-2025 00:00 AM (Gemini sometimes returns this)
        "%d/%m/%Y %H:%M %p",  # 28/09/2025 00:00 AM
        "%d-%m-%Y %H:%M",     # 08-11-2025 15:17
        "%d/%m/%Y %H:%M",     # 28/09/2025 15:17
        "%d-%m-%Y",           # 08-11-2025
        "%d/%m/%Y",           # 28/09/2025
        "%Y-%m-%d %H:%M:%S",  # 2025-11-08 15:17:00
        "%Y-%m-%d"            # 2025-11-08
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # If all formats fail
    error_msg = f"Failed to parse sample date '{date_str}' with any of the expected formats."
    logger.error(error_msg)
    raise ValueError(f"{error_msg} Expected format like: DD-MM-YYYY HH:MM AM/PM")
