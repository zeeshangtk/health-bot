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

