"""
Configuration module for Telegram health bot.
Uses Pydantic BaseSettings for validation - app fails fast if required config is missing.
"""
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    # Telegram Bot Token (Required)
    telegram_token: str = Field(
        ...,  # Required - no default means fail fast if missing
        description="Telegram bot token from @BotFather"
    )
    
    # Health Service API Configuration
    health_svc_api_url: str = Field(
        default="http://localhost:8000",
        description="URL of the Health Service API"
    )


# Supported Record Types
SUPPORTED_RECORD_TYPES: List[str] = [
    "BP",          # Blood Pressure
    "Sugar",       # Blood Sugar
    "Creatinine",  # Creatinine level
    "Weight",      # Weight measurement
    "Other"        # Other health records
]


# Create global settings instance - fails fast if required config is missing
settings = Settings()

# Backwards-compatible exports for existing code
TELEGRAM_TOKEN = settings.telegram_token
HEALTH_SVC_API_URL = settings.health_svc_api_url


def load_env() -> bool:
    """
    Check if configuration is valid.
    
    With Pydantic BaseSettings, this always returns True because
    the app would have already failed if TELEGRAM_TOKEN was missing.
    
    Returns:
        bool: True if configuration is valid
    """
    return True
