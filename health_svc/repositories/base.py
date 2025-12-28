"""
Base database connection and initialization.

This module handles database connection management and schema initialization.
"""
import sqlite3
import logging
from typing import Optional
from pathlib import Path

from core.config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """SQLite database connection manager."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Defaults to config DATABASE_PATH.
        """
        self.db_path = db_path or DATABASE_PATH
        
        # Ensure database directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        # Enable foreign key constraints (SQLite needs this explicitly)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # Create patients table first (referenced by foreign key)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create health_records table if it doesn't exist
        # Using IF NOT EXISTS to preserve existing data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                patient_id INTEGER NOT NULL,
                record_type TEXT NOT NULL,
                value TEXT NOT NULL,
                unit TEXT,
                lab_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection.
        
        Returns:
            sqlite3.Connection: A new database connection with foreign keys enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


# Global database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

