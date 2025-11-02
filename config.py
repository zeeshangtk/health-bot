"""
Configuration module for health bot.
Centralizes token, storage settings, and supported record types.
"""

import os
from typing import List


# Telegram Bot Token
# Load from TELEGRAM_TOKEN environment variable (recommended)
# Or set directly here if not using environment variables
# You can get a token from @BotFather on Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# Supported Record Types
SUPPORTED_RECORD_TYPES: List[str] = [
    "BP",          # Blood Pressure
    "Sugar",       # Blood Sugar
    "Creatinine",  # Creatinine level
    "Weight",      # Weight measurement
    "Other"        # Other health records
]


# Storage Configuration
STORAGE_MODE = "sqlite"

# SQLite database file path
# Database will be stored in a 'data' directory relative to the project root
DATABASE_DIR = "data"
DATABASE_FILE = "health_bot.db"
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)


def load_env():
    """
    Load configuration from environment variables if present.
    Since TELEGRAM_TOKEN is loaded directly from environment at module level,
    this function primarily serves as a check.
    
    Environment variable:
        TELEGRAM_TOKEN: The Telegram bot token (required)
    
    Returns:
        bool: True if token is available, False otherwise
    """
    return TELEGRAM_TOKEN is not None
