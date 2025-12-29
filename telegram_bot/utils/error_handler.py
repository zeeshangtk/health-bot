"""
Error handling utilities for Telegram bot.

This module provides:
- Normalized, user-friendly error messages
- No stack traces or internal details in user-facing messages
- Consistent error message formatting
- Error categorization for different handling

Design Choices:
- User-friendly language (no technical jargon)
- Actionable suggestions where possible
- Consistent emoji usage for error types
- Logging of full details while hiding from users

Usage:
    from utils.error_handler import format_error, handle_api_error
    
    try:
        await api_client.do_something()
    except Exception as e:
        message = format_error(e)
        await update.message.reply_text(message)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR MESSAGE TEMPLATES
# =============================================================================
# User-friendly error messages with no technical details.
# Each message includes an emoji and actionable suggestion.

ERROR_MESSAGES = {
    # Connection/network errors
    "connection": (
        "🔌 Unable to connect to the health service.\n\n"
        "Please check your internet connection and try again in a moment."
    ),
    "timeout": (
        "⏳ The request took too long to complete.\n\n"
        "Please try again. If this keeps happening, the service may be busy."
    ),
    
    # Data/validation errors
    "not_found": (
        "🔍 The requested item was not found.\n\n"
        "It may have been deleted or the name might be different."
    ),
    "patient_not_found": (
        "👤 Patient not found.\n\n"
        "Please check the name or add the patient first using /add_patient."
    ),
    "duplicate": (
        "⚠️ This item already exists.\n\n"
        "Please use a different name or check existing entries."
    ),
    "validation": (
        "📝 The information provided is not valid.\n\n"
        "Please check your input and try again."
    ),
    
    # Rate limiting
    "rate_limited": (
        "⏰ You're sending requests too quickly.\n\n"
        "Please wait a moment before trying again."
    ),
    
    # Authentication
    "unauthorized": (
        "🔒 Authentication failed.\n\n"
        "Please contact the administrator if this problem persists."
    ),
    
    # Server errors
    "server_error": (
        "⚠️ Something went wrong on our end.\n\n"
        "Please try again later. If this keeps happening, contact support."
    ),
    
    # Generic fallback
    "unknown": (
        "❌ An unexpected error occurred.\n\n"
        "Please try again. If the problem persists, contact support."
    ),
}


def classify_error(error: Exception) -> str:
    """
    Classify an error into a category for message selection.
    
    Args:
        error: The exception to classify.
    
    Returns:
        str: Error category key for ERROR_MESSAGES lookup.
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Connection errors
    if any(kw in error_str for kw in ['connection', 'network', 'refused', 'unreachable']):
        return "connection"
    if any(kw in error_str for kw in ['timeout', 'timed out']):
        return "timeout"
    if 'connectionerror' in error_type:
        return "connection"
    
    # HTTP status code patterns
    if '404' in error_str or 'not found' in error_str:
        if 'patient' in error_str:
            return "patient_not_found"
        return "not_found"
    if '409' in error_str or 'already exists' in error_str or 'duplicate' in error_str:
        return "duplicate"
    if '400' in error_str or 'validation' in error_str or 'invalid' in error_str:
        return "validation"
    if '429' in error_str or 'rate limit' in error_str:
        return "rate_limited"
    if '401' in error_str or '403' in error_str or 'unauthorized' in error_str:
        return "unauthorized"
    if '500' in error_str or '502' in error_str or '503' in error_str:
        return "server_error"
    
    # Fallback
    return "unknown"


def format_error(
    error: Exception,
    context: Optional[str] = None,
    log_full: bool = True
) -> str:
    """
    Format an exception as a user-friendly error message.
    
    This function:
    - Logs the full error details for debugging
    - Returns a sanitized, user-friendly message
    - Never exposes stack traces or internal details
    
    Args:
        error: The exception to format.
        context: Optional context about what operation failed (for logging).
        log_full: Whether to log the full error details (default: True).
    
    Returns:
        str: User-friendly error message safe for display.
    
    Example:
        try:
            await api_client.get_patients()
        except Exception as e:
            msg = format_error(e, context="fetching patients")
            await update.message.reply_text(msg)
    """
    # Log full error for debugging (with context if provided)
    if log_full:
        log_msg = f"Error occurred"
        if context:
            log_msg += f" while {context}"
        logger.error(log_msg, exc_info=error)
    
    # Classify and return user-friendly message
    category = classify_error(error)
    return ERROR_MESSAGES.get(category, ERROR_MESSAGES["unknown"])


def format_api_error(
    status_code: int,
    response_text: str,
    context: Optional[str] = None
) -> str:
    """
    Format an API error response as a user-friendly message.
    
    Args:
        status_code: HTTP status code from the API.
        response_text: Response body text (may contain technical details).
        context: Optional context about what operation failed.
    
    Returns:
        str: User-friendly error message.
    """
    # Log the full API error
    logger.error(
        f"API error",
        extra={
            "status_code": status_code,
            "response": response_text[:500],  # Truncate long responses
            "context": context
        }
    )
    
    # Map status codes to error categories
    if status_code == 404:
        if 'patient' in response_text.lower():
            return ERROR_MESSAGES["patient_not_found"]
        return ERROR_MESSAGES["not_found"]
    elif status_code == 409:
        return ERROR_MESSAGES["duplicate"]
    elif status_code == 400:
        return ERROR_MESSAGES["validation"]
    elif status_code == 429:
        return ERROR_MESSAGES["rate_limited"]
    elif status_code in (401, 403):
        return ERROR_MESSAGES["unauthorized"]
    elif status_code >= 500:
        return ERROR_MESSAGES["server_error"]
    else:
        return ERROR_MESSAGES["unknown"]


def get_retry_message(retry_seconds: float) -> str:
    """
    Format a rate-limiting message with retry time.
    
    This provides a friendlier message than the default rate limiter,
    converting seconds into a more human-readable format.
    
    Args:
        retry_seconds: Number of seconds until retry is allowed.
    
    Returns:
        str: Human-friendly rate limit message.
    """
    if retry_seconds < 1:
        return "⏰ Please wait a moment before trying again."
    elif retry_seconds < 60:
        secs = int(retry_seconds)
        return f"⏰ Please wait about {secs} second{'s' if secs != 1 else ''} before trying again."
    else:
        mins = int(retry_seconds / 60)
        return f"⏰ Please wait about {mins} minute{'s' if mins != 1 else ''} before trying again."

