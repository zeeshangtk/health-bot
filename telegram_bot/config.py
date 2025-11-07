"""
Configuration module for health bot.
Updated to use REST API instead of direct database access.
"""
import os
from typing import List

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Health Service API Configuration
HEALTH_SVC_API_URL = os.getenv(
    "HEALTH_SVC_API_URL",
    "http://localhost:8000"
)

# Supported Record Types
SUPPORTED_RECORD_TYPES: List[str] = [
    "BP",          # Blood Pressure
    "Sugar",       # Blood Sugar
    "Creatinine",  # Creatinine level
    "Weight",      # Weight measurement
    "Other"        # Other health records
]


def load_env():
    """
    Load configuration from environment variables.
    
    Environment variables:
        TELEGRAM_TOKEN: The Telegram bot token (required)
        HEALTH_SVC_API_URL: URL of the Health Service API (default: http://localhost:8000)
    
    Returns:
        bool: True if token is available, False otherwise
    """
    return TELEGRAM_TOKEN is not None
