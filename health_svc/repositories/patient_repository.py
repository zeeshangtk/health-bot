"""
Repository for patient database operations.

This module contains all database access for patient-related operations.
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any

from repositories.base import Database, get_database

logger = logging.getLogger(__name__)


class PatientRepository:
    """Repository for patient CRUD operations."""
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the patient repository.
        
        Args:
            db: Optional Database instance. If not provided, uses global instance.
        """
        self._db = db or get_database()
    
    def add(self, name: str) -> bool:
        """
        Add a new patient to the database.
        
        Args:
            name: Full name of the patient.
        
        Returns:
            bool: True if patient was added successfully, False if patient already exists.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO patients (name)
                VALUES (?)
            """, (name,))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Patient name already exists (UNIQUE constraint)
            return False
        finally:
            conn.close()
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all patients from the database, sorted alphabetically.
        
        Returns:
            List[dict]: List of patient dictionaries with id, name, and created_at.
        """
        conn = self._db.get_connection()
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
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a patient by name.
        
        Args:
            name: The patient's name.
        
        Returns:
            Optional[dict]: Patient dictionary or None if not found.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, created_at FROM patients WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "created_at": row[2]
            }
        return None
    
    def get_id_by_name(self, name: str) -> Optional[int]:
        """
        Get a patient's ID by their name.
        
        Args:
            name: The patient's name.
        
        Returns:
            Optional[int]: Patient ID or None if not found.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM patients WHERE name = ?", (name,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None

