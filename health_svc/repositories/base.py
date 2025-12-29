"""
Base database connection and initialization.

This module handles database connection management and schema initialization.
Optimized for SQLite concurrency with WAL mode and busy_timeout.

IMPORTANT: Database instantiation should be done through the DI layer.
Use core.dependencies.get_database() instead of instantiating directly.
This ensures proper lifecycle management and testability.
"""
import sqlite3
import logging
from typing import Optional
from pathlib import Path

from core.config import DATABASE_PATH, DATABASE_BUSY_TIMEOUT
from core.datetime_utils import utc_now, format_iso

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database connection manager with concurrency optimizations.
    
    Features:
    - WAL mode for better concurrent read/write performance
    - Busy timeout to handle lock contention gracefully
    - Foreign key constraints enabled by default
    - UTC timestamps for all database operations
    
    Usage:
        # Via dependency injection (recommended):
        from core.dependencies import get_database
        db = get_database()
        
        # Direct instantiation (for testing):
        db = Database(db_path="/tmp/test.db")
    """
    
    def __init__(self, db_path: Optional[str] = None, busy_timeout: Optional[int] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Defaults to config DATABASE_PATH.
            busy_timeout: SQLite busy timeout in milliseconds. Defaults to config value.
        """
        self.db_path = db_path or DATABASE_PATH
        self.busy_timeout = busy_timeout if busy_timeout is not None else DATABASE_BUSY_TIMEOUT
        
        # Ensure database directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema and configure pragmas
        self._init_db()
    
    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """
        Configure connection with optimal settings for concurrency.
        
        Args:
            conn: SQLite connection to configure.
        """
        # Set busy timeout to wait for locks instead of failing immediately
        conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout}")
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
    
    def _init_db(self) -> None:
        """Initialize database schema and enable WAL mode if not already enabled."""
        conn = sqlite3.connect(self.db_path)
        self._configure_connection(conn)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrent read/write performance
        # WAL mode persists in the database file, so this only needs to run once
        cursor.execute("PRAGMA journal_mode = WAL")
        result = cursor.fetchone()
        if result and result[0].lower() == 'wal':
            logger.info(f"SQLite WAL mode enabled for {self.db_path}")
        else:
            logger.warning(f"Failed to enable WAL mode, current mode: {result}")
        
        # Create patients table first (referenced by foreign key)
        # Note: created_at uses application-generated UTC timestamps for consistency
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
        
        logger.info(
            f"Database initialized: {self.db_path} "
            f"(busy_timeout={self.busy_timeout}ms)"
        )
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection with concurrency settings.
        
        Returns:
            sqlite3.Connection: A new database connection configured for
                concurrent access with foreign keys enabled and busy timeout set.
        """
        conn = sqlite3.connect(self.db_path)
        self._configure_connection(conn)
        return conn


# =============================================================================
# DEPRECATED: Global singleton pattern
# =============================================================================
# The following functions are DEPRECATED and kept for backward compatibility.
# Use core.dependencies.get_database() instead for proper DI.

_db_instance: Optional[Database] = None


def get_database() -> Database:
    """
    DEPRECATED: Get or create the global database instance.
    
    Use core.dependencies.get_database() instead for proper dependency injection.
    This function is kept for backward compatibility with existing code.
    """
    global _db_instance
    if _db_instance is None:
        logger.warning(
            "Using deprecated get_database() from repositories.base. "
            "Migrate to core.dependencies.get_database() for proper DI."
        )
        _db_instance = Database()
    return _db_instance


def reset_database_instance() -> None:
    """
    Reset the global database instance (for testing).
    
    DEPRECATED: Use core.dependencies.reset_database() instead.
    """
    global _db_instance
    _db_instance = None

