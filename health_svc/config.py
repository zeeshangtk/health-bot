"""
Configuration module for Health Service API service.
"""
import os
from pathlib import Path

# Database Configuration
DATABASE_DIR = os.getenv("HEALTH_SVC_DB_DIR", "data")
DATABASE_FILE = os.getenv("HEALTH_SVC_DB_FILE", "health_bot.db")
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)

# Ensure database directory exists
Path(DATABASE_DIR).mkdir(parents=True, exist_ok=True)

# API Configuration
API_HOST = os.getenv("HEALTH_SVC_HOST", "0.0.0.0")
API_PORT = int(os.getenv("HEALTH_SVC_PORT", "8000"))
API_RELOAD = os.getenv("HEALTH_SVC_RELOAD", "false").lower() == "true"

# Upload Configuration
UPLOAD_DIR = os.getenv("HEALTH_SVC_UPLOAD_DIR", "uploads")
UPLOAD_MAX_SIZE = int(os.getenv("HEALTH_SVC_UPLOAD_MAX_SIZE", "10485760"))  # 10MB in bytes

# Ensure upload directory exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

# Celery and Redis Configuration
REDIS_URL = os.getenv("HEALTH_SVC_REDIS_URL", "redis://localhost:6379")
REDIS_DB = int(os.getenv("HEALTH_SVC_REDIS_DB", "0"))

# Build Redis connection string with database selection
if REDIS_DB > 0:
    CELERY_BROKER_URL = f"{REDIS_URL}/{REDIS_DB}"
    CELERY_RESULT_BACKEND = f"{REDIS_URL}/{REDIS_DB}"
else:
    CELERY_BROKER_URL = f"{REDIS_URL}/0"
    CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"

CELERY_TASK_SERIALIZER = os.getenv("HEALTH_SVC_CELERY_TASK_SERIALIZER", "json")
CELERY_RESULT_SERIALIZER = os.getenv("HEALTH_SVC_CELERY_RESULT_SERIALIZER", "json")
CELERY_ACCEPT_CONTENT = os.getenv("HEALTH_SVC_CELERY_ACCEPT_CONTENT", "json").split(",")
CELERY_TIMEZONE = os.getenv("HEALTH_SVC_CELERY_TIMEZONE", "UTC")
CELERY_ENABLE_UTC = os.getenv("HEALTH_SVC_CELERY_ENABLE_UTC", "true").lower() == "true"

# Paperless NGX Configuration
PAPERLESS_NGX_URL = os.getenv("PAPERLESS_NGX_URL", "http://localhost:8000")
PAPERLESS_NGX_API_TOKEN = os.getenv("PAPERLESS_NGX_API_TOKEN", "")
PAPERLESS_NGX_TIMEOUT = int(os.getenv("PAPERLESS_NGX_TIMEOUT", "30"))  # seconds

