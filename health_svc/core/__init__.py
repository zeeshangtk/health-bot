"""
Core module for application configuration, logging, and shared constants.
"""
from core.config import settings, Settings
from core.config import (
    # Backwards-compatible exports
    DATABASE_DIR,
    DATABASE_FILE,
    DATABASE_PATH,
    API_HOST,
    API_PORT,
    API_RELOAD,
    UPLOAD_DIR,
    UPLOAD_MAX_SIZE,
    REDIS_URL,
    REDIS_DB,
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_TASK_SERIALIZER,
    CELERY_RESULT_SERIALIZER,
    CELERY_ACCEPT_CONTENT,
    CELERY_TIMEZONE,
    CELERY_ENABLE_UTC,
    PAPERLESS_NGX_URL,
    PAPERLESS_NGX_API_TOKEN,
    PAPERLESS_NGX_TIMEOUT,
    PAPERLESS_NGX_VERIFY_SSL,
    GEMINI_API_KEY,
)

# Metric registry exports
from core.metric_registry import (
    # Core API
    MetricDefinition,
    MetricConfig,  # Alias for backward compatibility
    get_metric,
    get_metric_config,
    list_metrics,
    is_abnormal,
    get_normal_range,
    # Utility functions
    parse_metric_value,
    parse_timestamp,
    calculate_trend,
    format_metric_value,
    # Constants
    DEFAULT_METRIC_CONFIG,
    RANGE_BAND_COLORS,
    DEFAULT_VISIBLE_METRICS,
)

__all__ = [
    "settings",
    "Settings",
    # Backwards-compatible exports
    "DATABASE_DIR",
    "DATABASE_FILE",
    "DATABASE_PATH",
    "API_HOST",
    "API_PORT",
    "API_RELOAD",
    "UPLOAD_DIR",
    "UPLOAD_MAX_SIZE",
    "REDIS_URL",
    "REDIS_DB",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "CELERY_TASK_SERIALIZER",
    "CELERY_RESULT_SERIALIZER",
    "CELERY_ACCEPT_CONTENT",
    "CELERY_TIMEZONE",
    "CELERY_ENABLE_UTC",
    "PAPERLESS_NGX_URL",
    "PAPERLESS_NGX_API_TOKEN",
    "PAPERLESS_NGX_TIMEOUT",
    "PAPERLESS_NGX_VERIFY_SSL",
    "GEMINI_API_KEY",
    # Metric registry exports
    "MetricDefinition",
    "MetricConfig",
    "get_metric",
    "get_metric_config",
    "list_metrics",
    "is_abnormal",
    "get_normal_range",
    "parse_metric_value",
    "parse_timestamp",
    "calculate_trend",
    "format_metric_value",
    "DEFAULT_METRIC_CONFIG",
    "RANGE_BAND_COLORS",
    "DEFAULT_VISIBLE_METRICS",
]

