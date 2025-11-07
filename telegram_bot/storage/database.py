"""
Database/storage implementation for health records.
"""
import os
import sqlite3
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from storage.models import HealthRecord

# Database configuration (temporary - will be moved to health_svc)
DATABASE_DIR = os.getenv("DATABASE_DIR", "data")
DATABASE_FILE = os.getenv("DATABASE_FILE", "health_bot.db")
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)


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
        
        # Check if health_records table exists and what columns it has
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='health_records'
        """)
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check if migration is needed (check if patient column exists)
            cursor.execute("PRAGMA table_info(health_records)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'patient_id' in columns:
                # Already migrated, nothing to do
                pass
            elif 'patient' in columns:
                # Need to migrate from patient TEXT to patient_id INTEGER
                self._migrate_to_foreign_key(conn, cursor)
            else:
                # Table exists but has neither patient nor patient_id - recreate with correct schema
                cursor.execute("DROP TABLE IF EXISTS health_records")
                cursor.execute("""
                    CREATE TABLE health_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        patient_id INTEGER NOT NULL,
                        record_type TEXT NOT NULL,
                        data_type TEXT NOT NULL,
                        value TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (patient_id) REFERENCES patients(id)
                    )
                """)
        else:
            # Create table with foreign key from scratch
            cursor.execute("""
                CREATE TABLE health_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    patient_id INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            """)
        
        conn.commit()
        conn.close()
    
    def _migrate_to_foreign_key(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
        """
        Migrate existing health_records table from patient TEXT to patient_id INTEGER.
        """
        # Add patient_id column
        cursor.execute("""
            ALTER TABLE health_records ADD COLUMN patient_id INTEGER
        """)
        
        # For each unique patient name in health_records, create/update patient entry
        cursor.execute("SELECT DISTINCT patient FROM health_records")
        patient_names = [row[0] for row in cursor.fetchall()]
        
        for patient_name in patient_names:
            # Get or create patient
            cursor.execute("SELECT id FROM patients WHERE name = ?", (patient_name,))
            result = cursor.fetchone()
            
            if result:
                patient_id = result[0]
            else:
                # Create new patient
                cursor.execute("INSERT INTO patients (name) VALUES (?)", (patient_name,))
                patient_id = cursor.lastrowid
            
            # Update health_records with patient_id
            cursor.execute("""
                UPDATE health_records 
                SET patient_id = ? 
                WHERE patient = ?
            """, (patient_id, patient_name))
        
        # Drop old patient column and rename table temporarily
        cursor.execute("""
            CREATE TABLE health_records_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                patient_id INTEGER NOT NULL,
                record_type TEXT NOT NULL,
                data_type TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        # Copy data
        cursor.execute("""
            INSERT INTO health_records_new 
            (id, timestamp, patient_id, record_type, data_type, value, created_at)
            SELECT id, timestamp, patient_id, record_type, data_type, value, created_at
            FROM health_records
        """)
        
        # Replace old table
        cursor.execute("DROP TABLE health_records")
        cursor.execute("ALTER TABLE health_records_new RENAME TO health_records")
    
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
            patient: Name of the patient (will be looked up to get patient_id)
            record_type: Type of record (BP, Sugar, Creatinine, Weight, Other)
            data_type: Type of data (e.g., "text", "number", "reading")
            value: The recorded value
        
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
            (timestamp, patient_id, record_type, data_type, value)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp.isoformat(),
            patient_id,
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
            List of HealthRecord objects with patient name resolved from foreign key
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use JOIN to get patient name from patients table
        query = """
            SELECT hr.timestamp, p.name, hr.record_type, hr.data_type, hr.value 
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


# Global database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
