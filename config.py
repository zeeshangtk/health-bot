"""
Configuration module for health bot.
Centralizes token, patient list, storage settings, and supported record types.
"""

import os
from typing import List


# Telegram Bot Token
# TODO: Replace this placeholder with your actual Telegram bot token
# You can get a token from @BotFather on Telegram
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"


# Patient Names List
# Update this list with actual patient names
PATIENT_NAMES: List[str] = [
    "Nazra Mastoor",
    "Asgar Ali Ansari"
]


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
    This function checks for TELEGRAM_TOKEN in environment variables
    and updates the config if found.
    
    Environment variable:
        TELEGRAM_TOKEN: The Telegram bot token (optional)
    
    Returns:
        bool: True if token was loaded from env, False otherwise
    """
    global TELEGRAM_TOKEN
    
    env_token = os.getenv("TELEGRAM_TOKEN")
    if env_token:
        TELEGRAM_TOKEN = env_token
        return True
    return False
