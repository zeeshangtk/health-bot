"""
Repository for patient database operations.

This module contains all database access for patient-related operations.

Architecture:
    PatientRepository is the data access layer for patients.
    It should be injected via core.dependencies.get_patient_repository().
    
All SQL is encapsulated in this repository - no SQL in service or API layers.
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any

from repositories.base import Database

logger = logging.getLogger(__name__)


class PatientRepository:
    """
    Repository for patient CRUD operations.
    
    This repository encapsulates all database operations for patients.
    It should be instantiated via core.dependencies.get_patient_repository().
    """
    
    def __init__(self, db: Database):
        """
        Initialize the patient repository.
        
        Args:
            db: Database instance for data access.
                Injected via core.dependencies.get_patient_repository().
        """
        self._db = db
    
    def add(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Add a new patient to the database and return the created record.
        
        Uses a single transaction to insert and retrieve the record,
        avoiding race conditions that could occur if we queried separately.
        
        Args:
            name: Full name of the patient.
        
        Returns:
            Optional[Dict[str, Any]]: The created patient dict with id, name, and created_at,
                or None if patient already exists (UNIQUE constraint violation).
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO patients (name)
                VALUES (?)
            """, (name,))
            
            # Get the inserted row using lastrowid within the same transaction
            # This is safe because we're in the same connection/transaction
            patient_id = cursor.lastrowid
            
            # Fetch the complete record to get the created_at timestamp
            cursor.execute(
                "SELECT id, name, created_at FROM patients WHERE id = ?",
                (patient_id,)
            )
            row = cursor.fetchone()
            
            conn.commit()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2]
                }
            return None
        except sqlite3.IntegrityError:
            # Patient name already exists (UNIQUE constraint)
            return None
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

