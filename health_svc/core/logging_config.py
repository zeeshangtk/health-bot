"""
Structured JSON logging configuration for Grafana/Loki compatibility.

This module provides:
- JSON-formatted log output for Grafana Loki ingestion
- Request ID propagation via contextvars
- Consistent log structure across all services
- Low-overhead logging suitable for Raspberry Pi

Design Choices:
- Uses stdlib logging with custom JSONFormatter (no heavy dependencies)
- Contextvar-based request_id for coroutine-safe propagation
- Configurable log level via environment variable
- Outputs to stdout for container/systemd log collection

Log Structure (JSON):
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "logger": "health_svc.api",
    "message": "Request completed",
    "request_id": "abc-123",
    "extra": { ... }
}

Usage:
    from core.logging_config import setup_logging, get_request_id
    
    # At app startup
    setup_logging()
    
    # In request handlers (request_id is auto-propagated by middleware)
    logger.info("Processing request", extra={"patient": "John"})
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# =============================================================================
# REQUEST ID CONTEXT
# =============================================================================
# ContextVar ensures request_id is coroutine-safe in async handlers.
# Each request gets a unique ID that propagates through all log statements.

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context (coroutine-safe)."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context for the current request/coroutine."""
    request_id_var.set(request_id)


def clear_request_id() -> None:
    """Clear the request ID (call at end of request)."""
    request_id_var.set(None)


# =============================================================================
# JSON FORMATTER
# =============================================================================

class JSONFormatter(logging.Formatter):
    """
    JSON log formatter optimized for Grafana Loki.
    
    Produces single-line JSON logs with consistent structure.
    All timestamps are UTC for Grafana time-series alignment.
    
    Raspberry Pi considerations:
    - Minimal string operations
    - No external dependencies
    - Compact output (no pretty-printing)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as single-line JSON."""
        # Base log structure - these fields are always present
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request_id if present in context (propagated by middleware)
        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the log call (e.g., logger.info("msg", extra={...}))
        # Filter out standard LogRecord attributes
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "taskName", "message"
        }
        
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_attrs and not key.startswith("_")
        }
        
        if extra:
            log_entry["extra"] = extra
        
        # Single-line JSON (no indent) for efficient log shipping
        return json.dumps(log_entry, default=str, ensure_ascii=False)


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    include_uvicorn: bool = True
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON format; if False, use human-readable format
        include_uvicorn: If True, also configure uvicorn loggers
    
    Called once at application startup (in main.py lifespan).
    
    Environment Variables:
        LOG_LEVEL: Override the log level (default: INFO)
        LOG_FORMAT: Override format ("json" or "text", default: json)
    """
    import os
    
    # Allow environment override
    level = os.environ.get("LOG_LEVEL", level).upper()
    json_format = os.environ.get("LOG_FORMAT", "json" if json_format else "text").lower() == "json"
    
    # Create handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        # Human-readable format for local development
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]
    
    # Configure application loggers
    for logger_name in ["health_svc", "core", "api", "services", "repositories", "tasks"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.handlers = []  # Inherit from root
        logger.propagate = True
    
    # Configure uvicorn loggers (if running under uvicorn)
    if include_uvicorn:
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            logger = logging.getLogger(logger_name)
            logger.handlers = []
            logger.propagate = True
    
    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"level": level, "format": "json" if json_format else "text"}
    )


# =============================================================================
# CONVENIENCE LOGGER
# =============================================================================

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Convenience function that ensures consistent logger naming.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

