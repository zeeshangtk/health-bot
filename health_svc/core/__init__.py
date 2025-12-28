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
]

