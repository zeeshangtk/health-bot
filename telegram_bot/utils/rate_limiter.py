"""
Rate limiting utility for Telegram bot handlers.

Provides per-user rate limiting to prevent abuse and ensure fair usage.
Uses an in-memory sliding window approach for simplicity.
"""
import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Optional, Dict, List, Tuple

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Tracks request timestamps per user and enforces limits on:
    - Maximum requests within a time window
    - Minimum interval between requests (burst protection)
    """
    
    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        min_interval_seconds: float = 1.0,
        cleanup_interval: int = 300
    ):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed within the window.
            window_seconds: Size of the sliding window in seconds.
            min_interval_seconds: Minimum seconds between consecutive requests.
            cleanup_interval: Seconds between cleanup of old entries.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.min_interval_seconds = min_interval_seconds
        self.cleanup_interval = cleanup_interval
        
        # user_id -> list of request timestamps
        self._requests: Dict[int, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self) -> None:
        """Remove expired entries to prevent memory growth."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self.cleanup_interval:
            return
        
        cutoff = current_time - self.window_seconds
        users_to_remove = []
        
        for user_id, timestamps in self._requests.items():
            # Remove old timestamps
            self._requests[user_id] = [ts for ts in timestamps if ts > cutoff]
            
            # Mark empty entries for removal
            if not self._requests[user_id]:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self._requests[user_id]
        
        self._last_cleanup = current_time
        logger.debug(f"Rate limiter cleanup: removed {len(users_to_remove)} inactive users")
    
    def is_allowed(self, user_id: int) -> Tuple[bool, Optional[float]]:
        """
        Check if a request from the user is allowed.
        
        Args:
            user_id: Telegram user ID.
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds).
            If allowed, retry_after is None.
            If not allowed, retry_after indicates when they can try again.
        """
        current_time = time.time()
        self._cleanup_old_entries()
        
        # Get user's request history
        timestamps = self._requests[user_id]
        cutoff = current_time - self.window_seconds
        
        # Filter to only requests within the window
        recent_timestamps = [ts for ts in timestamps if ts > cutoff]
        
        # Check burst protection (minimum interval)
        if recent_timestamps:
            last_request = recent_timestamps[-1]
            time_since_last = current_time - last_request
            
            if time_since_last < self.min_interval_seconds:
                retry_after = self.min_interval_seconds - time_since_last
                return False, retry_after
        
        # Check window limit
        if len(recent_timestamps) >= self.max_requests:
            # Calculate when the oldest request will expire
            oldest_in_window = min(recent_timestamps)
            retry_after = (oldest_in_window + self.window_seconds) - current_time
            return False, max(0.1, retry_after)
        
        # Request is allowed - record it
        recent_timestamps.append(current_time)
        self._requests[user_id] = recent_timestamps
        
        return True, None
    
    def get_remaining(self, user_id: int) -> int:
        """Get the number of remaining requests for a user."""
        current_time = time.time()
        cutoff = current_time - self.window_seconds
        
        timestamps = self._requests.get(user_id, [])
        recent_count = sum(1 for ts in timestamps if ts > cutoff)
        
        return max(0, self.max_requests - recent_count)


# Global rate limiter instances with different limits for different operations
_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(
    name: str = "default",
    max_requests: int = 10,
    window_seconds: int = 60,
    min_interval_seconds: float = 1.0
) -> RateLimiter:
    """
    Get or create a named rate limiter.
    
    Args:
        name: Unique name for this rate limiter configuration.
        max_requests: Maximum requests in the window.
        window_seconds: Window size in seconds.
        min_interval_seconds: Minimum interval between requests.
    
    Returns:
        RateLimiter instance.
    """
    if name not in _limiters:
        _limiters[name] = RateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
            min_interval_seconds=min_interval_seconds
        )
    return _limiters[name]


def _format_rate_limit_message(retry_after: float) -> str:
    """
    Format a human-friendly rate limiting message.
    
    Args:
        retry_after: Seconds until retry is allowed.
    
    Returns:
        User-friendly rate limit message.
    """
    if retry_after < 1:
        return "⏰ Please wait a moment before trying again."
    elif retry_after < 60:
        secs = int(retry_after)
        return f"⏰ Please wait about {secs} second{'s' if secs != 1 else ''} before trying again."
    else:
        mins = int(retry_after / 60)
        return f"⏰ Please wait about {mins} minute{'s' if mins != 1 else ''} before trying again."


def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60,
    min_interval_seconds: float = 1.0,
    limiter_name: Optional[str] = None,
    on_limited_message: Optional[str] = None
) -> Callable:
    """
    Decorator to apply rate limiting to Telegram bot handlers.
    
    Uses human-friendly messages that avoid technical jargon.
    
    Args:
        max_requests: Maximum requests allowed in the window.
        window_seconds: Size of the sliding window in seconds.
        min_interval_seconds: Minimum seconds between consecutive requests.
        limiter_name: Optional name for a shared rate limiter. If None, uses handler function name.
        on_limited_message: Optional custom message. If None, uses human-friendly default.
    
    Returns:
        Decorated handler function.
    
    Example:
        @rate_limit(max_requests=5, window_seconds=60)
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            ...
    """
    def decorator(func: Callable) -> Callable:
        name = limiter_name or func.__name__
        limiter = get_rate_limiter(
            name=name,
            max_requests=max_requests,
            window_seconds=window_seconds,
            min_interval_seconds=min_interval_seconds
        )
        
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            # Get user ID from update
            user = update.effective_user
            if not user:
                # Can't rate limit without user info, allow the request
                return await func(update, context, *args, **kwargs)
            
            user_id = user.id
            is_allowed, retry_after = limiter.is_allowed(user_id)
            
            if not is_allowed:
                # Log with structured fields (for backend aggregation if needed)
                logger.warning(
                    "Rate limited user",
                    extra={
                        "user_id": user_id,
                        "username": user.username,
                        "handler": name,
                        "retry_after_seconds": round(retry_after, 1)
                    }
                )
                
                # Send human-friendly rate limit message
                if on_limited_message:
                    message = on_limited_message.format(retry_after=retry_after)
                else:
                    message = _format_rate_limit_message(retry_after)
                
                if update.callback_query:
                    await update.callback_query.answer(message, show_alert=True)
                elif update.message:
                    await update.message.reply_text(message)
                
                return None
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    
    return decorator


# Pre-configured decorators for common use cases
def rate_limit_commands(func: Callable) -> Callable:
    """Rate limit for regular commands: 10 requests per minute."""
    return rate_limit(
        max_requests=10,
        window_seconds=60,
        min_interval_seconds=0.5,
        limiter_name="commands"
    )(func)


def rate_limit_uploads(func: Callable) -> Callable:
    """
    Rate limit for file uploads: 5 per minute (more restrictive).
    Uses human-friendly message.
    """
    return rate_limit(
        max_requests=5,
        window_seconds=60,
        min_interval_seconds=2.0,
        limiter_name="uploads",
        on_limited_message="⏰ Please wait a moment before uploading another file."
    )(func)


def rate_limit_api_calls(func: Callable) -> Callable:
    """Rate limit for API-heavy operations: 15 per minute."""
    return rate_limit(
        max_requests=15,
        window_seconds=60,
        min_interval_seconds=0.3,
        limiter_name="api_calls"
    )(func)

