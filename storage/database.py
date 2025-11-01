"""
Database/storage implementation for health records.
"""
import os
import sqlite3
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from config import DATABASE_DIR, DATABASE_PATH
from storage.models import HealthRecord


class Database:
    """SQLite database handler for health records."""
    
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
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                patient TEXT NOT NULL,
                record_type TEXT NOT NULL,
                data_type TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # NEW: Create patients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        data_type: str,
        value: str
    ) -> int:
        """
        Save a health record to the database.
        
        Args:
            timestamp: When the record was created
            patient: Name of the patient
            record_type: Type of record (BP, Sugar, Creatinine, Weight, Other)
            data_type: Type of data (e.g., "text", "number", "reading")
            value: The recorded value
        
        Returns:
            int: The ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO health_records 
            (timestamp, patient, record_type, data_type, value)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp.isoformat(),
            patient,
            record_type,
            data_type,
            value
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_records(
        self,
        patient: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[HealthRecord]:
        """
        Retrieve health records from the database.
        
        Args:
            patient: Filter by patient name (optional)
            record_type: Filter by record type (optional)
            limit: Maximum number of records to return (optional)
        
        Returns:
            List of HealthRecord objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT timestamp, patient, record_type, data_type, value FROM health_records WHERE 1=1"
        params = []
        
        if patient:
            query += " AND patient = ?"
            params.append(patient)
        
        if record_type:
            query += " AND record_type = ?"
            params.append(record_type)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append(HealthRecord(
                timestamp=datetime.fromisoformat(row[0]),
                patient=row[1],
                record_type=row[2],
                data_type=row[3],
                value=row[4]
            ))
        
        return records
    
    def add_patient(self, name: str) -> bool:
        """
        Add a new patient to the database.
        
        Args:
            name: Full name of the patient
        
        Returns:
            bool: True if patient was added successfully, False if patient already exists
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO patients (name)
                VALUES (?)
            """, (name,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Patient name already exists (UNIQUE constraint)
            conn.close()
            return False
    
    def get_patients(self) -> List[str]:
        """
        Get all patients from the database, sorted alphabetically.
        
        Returns:
            List[str]: List of patient names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM patients
            ORDER BY name ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]


# Global database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
