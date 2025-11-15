"""
Database/storage implementation for health records.
"""
import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from config import DATABASE_DIR, DATABASE_PATH
from storage.models import HealthRecord

logger = logging.getLogger(__name__)


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
    
    def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        value: str,
        unit: Optional[str] = None,
        lab_name: Optional[str] = "self"
    ) -> int:
        """
        Save a health record to the database.
        
        Args:
            timestamp: When the record was created
            patient: Name of the patient (will be looked up to get patient_id)
            record_type: Type of record (BP, Sugar, Creatinine, Weight, Other)
            value: The recorded value
            unit: Unit of measurement (optional)
            lab_name: Name of the lab (optional, defaults to "self")
        
        Returns:
            int: The ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # Get patient_id from patient name
        cursor.execute("SELECT id FROM patients WHERE name = ?", (patient,))
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"Patient '{patient}' not found in database")
        
        patient_id = result[0]
        
        cursor.execute("""
            INSERT INTO health_records 
            (timestamp, patient_id, record_type, value, unit, lab_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp.isoformat(),
            patient_id,
            record_type,
            value,
            unit,
            lab_name
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
            List of HealthRecord objects with patient name resolved from foreign key
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use JOIN to get patient name from patients table
        query = """
            SELECT hr.timestamp, p.name, hr.record_type, hr.value, hr.unit, hr.lab_name 
            FROM health_records hr
            INNER JOIN patients p ON hr.patient_id = p.id
            WHERE 1=1
        """
        params = []
        
        if patient:
            query += " AND p.name = ?"
            params.append(patient)
        
        if record_type:
            query += " AND hr.record_type = ?"
            params.append(record_type)
        
        query += " ORDER BY hr.timestamp DESC"
        
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
                patient=row[1],  # Patient name from JOIN
                record_type=row[2],
                value=row[3],
                unit=row[4],
                lab_name=row[5] if row[5] is not None else "self"
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
    
    def get_patients(self) -> List[dict]:
        """
        Get all patients from the database, sorted alphabetically.
        
        Returns:
            List[dict]: List of patient dictionaries with id, name, and created_at
            Example:
            [
                {"id": 1, "name": "Mom", "created_at": "2025-11-01 10:23:00"},
                {"id": 2, "name": "Dad", "created_at": "2025-11-01 10:25:00"}
            ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, created_at FROM patients
            ORDER BY name ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "created_at": row[2]
            }
            for row in rows
        ]
    
    def save_lab_report_records(
        self,
        patient_name: str,
        timestamp: datetime,
        lab_name: str,
        test_results: List[dict]
    ) -> List[int]:
        """
        Save multiple health records from a lab report atomically (all or nothing).
        
        This method ensures that either all test results are saved or none are saved.
        The patient must exist in the database; if not, the operation will fail.
        
        Args:
            patient_name: Name of the patient (must exist in database)
            timestamp: When the sample was collected (used for all records)
            lab_name: Name of the laboratory/hospital
            test_results: List of test result dictionaries with keys:
                - test_name: Name of the test (maps to record_type)
                - results: Test result value (maps to value)
                - unit: Unit of measurement (maps to unit)
        
        Returns:
            List[int]: List of inserted record IDs
        
        Raises:
            ValueError: If patient is not found in database
            sqlite3.Error: If database transaction fails
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        try:
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Get patient - must exist, fail if not found
            cursor.execute("SELECT id FROM patients WHERE name = ?", (patient_name,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f"Patient '{patient_name}' not found in database")
            
            patient_id = result[0]
            
            # Prepare all records for batch insert
            record_ids = []
            timestamp_iso = timestamp.isoformat()
            
            for test_result in test_results:
                cursor.execute("""
                    INSERT INTO health_records 
                    (timestamp, patient_id, record_type, value, unit, lab_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_iso,
                    patient_id,
                    test_result["test_name"],
                    test_result["results"],
                    test_result.get("unit"),
                    lab_name
                ))
                record_ids.append(cursor.lastrowid)
            
            # Commit transaction (all or nothing)
            conn.commit()
            logger.info(
                f"Successfully saved {len(record_ids)} lab report records "
                f"for patient '{patient_name}' atomically"
            )
            
            return record_ids
            
        except Exception as e:
            # Rollback on any error
            conn.rollback()
            logger.error(
                f"Error saving lab report records for patient '{patient_name}': {str(e)}. "
                "Transaction rolled back."
            )
            raise
        finally:
            conn.close()


# Global database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

