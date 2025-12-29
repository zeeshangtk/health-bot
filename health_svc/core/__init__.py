"""
Core module for application configuration, logging, and shared constants.

This module provides:
- Settings: Application configuration via pydantic-settings
- Dependency injection: FastAPI Depends() functions for services and repositories
- Exceptions: Domain-specific exception classes with HTTP status codes
- Datetime utilities: UTC-first datetime handling
- Metric registry: Health metric definitions and parsing
"""
from core.config import settings, Settings

# Dependency injection - import functions for FastAPI Depends()
from core.dependencies import (
    get_database,
    get_patient_repository,
    get_health_record_repository,
    get_patient_service,
    get_health_service,
    get_graph_service,
    get_upload_service,
    reset_database,
)

# Exception classes for consistent error handling
from core.exceptions import (
    HealthServiceError,
    PatientNotFoundError,
    DuplicatePatientError,
    RecordNotFoundError,
    InvalidRecordDataError,
    DatabaseError,
    UploadError,
    InvalidFileTypeError,
    FileTooLargeError,
    ExternalServiceError,
    GeminiServiceError,
    setup_exception_handlers,
)

# UTC datetime utilities
from core.datetime_utils import (
    utc_now,
    to_utc,
    parse_datetime,
    format_iso,
    to_db_string,
    from_db_string,
)
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
    # Settings
    "settings",
    "Settings",
    # Dependency injection
    "get_database",
    "get_patient_repository",
    "get_health_record_repository",
    "get_patient_service",
    "get_health_service",
    "get_graph_service",
    "get_upload_service",
    "reset_database",
    # Exceptions
    "HealthServiceError",
    "PatientNotFoundError",
    "DuplicatePatientError",
    "RecordNotFoundError",
    "InvalidRecordDataError",
    "DatabaseError",
    "UploadError",
    "InvalidFileTypeError",
    "FileTooLargeError",
    "ExternalServiceError",
    "GeminiServiceError",
    "setup_exception_handlers",
    # Datetime utilities
    "utc_now",
    "to_utc",
    "parse_datetime",
    "format_iso",
    "to_db_string",
    "from_db_string",
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

