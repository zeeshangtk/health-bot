"""
Configuration module for Health Service API service.
Uses Pydantic BaseSettings for validation - app fails fast if required config is missing.
"""
import sys
import logging
from pathlib import Path
from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with validation.
    Required fields will cause the app to fail fast if not provided.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Database Configuration
    health_svc_db_dir: str = Field(default="data", description="Database directory")
    health_svc_db_file: str = Field(default="health_bot.db", description="Database filename")
    health_svc_db_busy_timeout: int = Field(default=5000, description="SQLite busy timeout in milliseconds")
    
    # API Configuration
    health_svc_host: str = Field(default="0.0.0.0", description="API host")
    health_svc_port: int = Field(default=8000, description="API port")
    health_svc_reload: bool = Field(default=False, description="Enable hot reload")
    
    # Upload Configuration
    health_svc_upload_dir: str = Field(default="uploads", description="Upload directory")
    health_svc_upload_max_size: int = Field(default=10485760, description="Max upload size in bytes (10MB)")
    
    # Redis & Celery Configuration
    health_svc_redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    health_svc_redis_db: int = Field(default=0, description="Redis database number")
    health_svc_celery_task_serializer: str = Field(default="json", description="Celery task serializer")
    health_svc_celery_result_serializer: str = Field(default="json", description="Celery result serializer")
    health_svc_celery_accept_content: str = Field(default="json", description="Celery accepted content types (comma-separated)")
    health_svc_celery_timezone: str = Field(default="UTC", description="Celery timezone")
    health_svc_celery_enable_utc: bool = Field(default=True, description="Enable UTC for Celery")
    
    # Paperless NGX Configuration (Optional)
    paperless_ngx_url: str = Field(default="http://localhost:8000", description="Paperless NGX URL")
    paperless_ngx_api_token: str = Field(default="", description="Paperless NGX API token")
    paperless_ngx_timeout: int = Field(default=30, description="Paperless NGX timeout in seconds")
    paperless_ngx_verify_ssl: bool = Field(default=True, description="Verify SSL for Paperless NGX")
    
    # Google Gemini API Configuration (Required for document parsing)
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    
    # API Authentication Configuration
    health_svc_api_key: str = Field(
        ...,  # Required - no default means fail fast if missing
        description="API key for authenticating requests to the Health Service API",
        min_length=32,  # Enforce minimum key length for security
    )
    
    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """
        Validate required secrets at startup and fail fast with clear error messages.
        This ensures all required configuration is present before the app starts.
        """
        errors = []
        
        # Check Gemini API key if upload features are expected to work
        if not self.gemini_api_key:
            logger.warning(
                "GEMINI_API_KEY not set - document upload/parsing features will be disabled"
            )
        
        # Check Paperless NGX token if URL is configured
        if self.paperless_ngx_url and self.paperless_ngx_url != "http://localhost:8000":
            if not self.paperless_ngx_api_token:
                logger.warning(
                    "PAPERLESS_NGX_URL is configured but PAPERLESS_NGX_API_TOKEN is not set - "
                    "Paperless NGX integration will not work"
                )
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.critical(error_msg)
            sys.exit(1)
        
        return self
    
    @property
    def database_path(self) -> str:
        """Get the full database path."""
        return str(Path(self.health_svc_db_dir) / self.health_svc_db_file)
    
    @property
    def celery_broker_url(self) -> str:
        """Get the Celery broker URL with database selection."""
        return f"{self.health_svc_redis_url}/{self.health_svc_redis_db}"
    
    @property
    def celery_result_backend(self) -> str:
        """Get the Celery result backend URL with database selection."""
        return f"{self.health_svc_redis_url}/{self.health_svc_redis_db}"
    
    @property
    def celery_accept_content_list(self) -> List[str]:
        """Get the Celery accepted content types as a list."""
        return [c.strip() for c in self.health_svc_celery_accept_content.split(",")]
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        Path(self.health_svc_db_dir).mkdir(parents=True, exist_ok=True)
        Path(self.health_svc_upload_dir).mkdir(parents=True, exist_ok=True)


# Create global settings instance - fails fast if required config is missing
settings = Settings()

# Ensure directories exist on import
settings.ensure_directories()

# Backwards-compatible exports for existing code
DATABASE_DIR = settings.health_svc_db_dir
DATABASE_FILE = settings.health_svc_db_file
DATABASE_PATH = settings.database_path
DATABASE_BUSY_TIMEOUT = settings.health_svc_db_busy_timeout

API_HOST = settings.health_svc_host
API_PORT = settings.health_svc_port
API_RELOAD = settings.health_svc_reload

UPLOAD_DIR = settings.health_svc_upload_dir
UPLOAD_MAX_SIZE = settings.health_svc_upload_max_size

REDIS_URL = settings.health_svc_redis_url
REDIS_DB = settings.health_svc_redis_db
CELERY_BROKER_URL = settings.celery_broker_url
CELERY_RESULT_BACKEND = settings.celery_result_backend
CELERY_TASK_SERIALIZER = settings.health_svc_celery_task_serializer
CELERY_RESULT_SERIALIZER = settings.health_svc_celery_result_serializer
CELERY_ACCEPT_CONTENT = settings.celery_accept_content_list
CELERY_TIMEZONE = settings.health_svc_celery_timezone
CELERY_ENABLE_UTC = settings.health_svc_celery_enable_utc

PAPERLESS_NGX_URL = settings.paperless_ngx_url
PAPERLESS_NGX_API_TOKEN = settings.paperless_ngx_api_token
PAPERLESS_NGX_TIMEOUT = settings.paperless_ngx_timeout
PAPERLESS_NGX_VERIFY_SSL = settings.paperless_ngx_verify_ssl

GEMINI_API_KEY = settings.gemini_api_key

API_KEY = settings.health_svc_api_key

