"""
Repository for health record database operations.

This module contains all database access for health record-related operations.
Uses single-transaction patterns to avoid race conditions when returning created records.

Architecture:
    HealthRecordRepository is the data access layer for health records.
    It should be injected via core.dependencies.get_health_record_repository().
    
All SQL is encapsulated in this repository - no SQL in service or API layers.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from repositories.base import Database
from models.health_record import HealthRecord
from core.datetime_utils import format_iso, parse_datetime

logger = logging.getLogger(__name__)


class HealthRecordRepository:
    """
    Repository for health record CRUD operations.
    
    This repository encapsulates all database operations for health records.
    It should be instantiated via core.dependencies.get_health_record_repository().
    """
    
    def __init__(self, db: Database):
        """
        Initialize the health record repository.
        
        Args:
            db: Database instance for data access.
                Injected via core.dependencies.get_health_record_repository().
        """
        self._db = db
    
    def save(
        self,
        timestamp: datetime,
        patient_id: int,
        record_type: str,
        value: str,
        unit: Optional[str] = None,
        lab_name: Optional[str] = "self"
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Save a health record to the database and return the complete record.
        
        Uses a single transaction to insert and retrieve the record,
        avoiding race conditions that could occur if we queried separately.
        
        Args:
            timestamp: When the record was created.
            patient_id: ID of the patient.
            record_type: Type of record (BP, Sugar, Creatinine, Weight, Other).
            value: The recorded value.
            unit: Unit of measurement (optional).
            lab_name: Name of the lab (optional, defaults to "self").
        
        Returns:
            Tuple[int, Dict[str, Any]]: A tuple of (record_id, record_dict) where
                record_dict contains the complete record with patient name resolved.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Format timestamp as ISO 8601 UTC string for storage
            timestamp_str = format_iso(timestamp)
            
            cursor.execute("""
                INSERT INTO health_records 
                (timestamp, patient_id, record_type, value, unit, lab_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp_str,
                patient_id,
                record_type,
                value,
                unit,
                lab_name
            ))
            
            record_id = cursor.lastrowid
            
            # Fetch the complete record with patient name within the same transaction
            cursor.execute("""
                SELECT hr.id, hr.timestamp, p.name, hr.record_type, hr.value, 
                       hr.unit, hr.lab_name, hr.created_at
                FROM health_records hr
                INNER JOIN patients p ON hr.patient_id = p.id
                WHERE hr.id = ?
            """, (record_id,))
            row = cursor.fetchone()
            
            conn.commit()
            
            record_dict = {
                "id": row[0],
                "timestamp": row[1],
                "patient": row[2],
                "record_type": row[3],
                "value": row[4],
                "unit": row[5],
                "lab_name": row[6] if row[6] is not None else "self",
                "created_at": row[7]
            }
            
            return record_id, record_dict
        finally:
            conn.close()
    
    def get_all(
        self,
        patient_name: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[HealthRecord]:
        """
        Retrieve health records from the database.
        
        Args:
            patient_name: Filter by patient name (optional).
            record_type: Filter by record type (optional).
            limit: Maximum number of records to return (optional).
        
        Returns:
            List of HealthRecord objects with patient name resolved from foreign key.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        # Use JOIN to get patient name from patients table
        query = """
            SELECT hr.id, hr.timestamp, p.name, hr.record_type, hr.value, hr.unit, hr.lab_name
            FROM health_records hr
            INNER JOIN patients p ON hr.patient_id = p.id
            WHERE 1=1
        """
        params = []
        
        if patient_name:
            query += " AND p.name = ?"
            params.append(patient_name)
        
        if record_type:
            query += " AND hr.record_type LIKE ?"
            params.append(f"%{record_type}%")
        
        query += " ORDER BY hr.timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            # Parse timestamp using our UTC-aware utility
            timestamp = parse_datetime(row[1])
            records.append(HealthRecord(
                id=row[0],
                timestamp=timestamp,
                patient=row[2],  # Patient name from JOIN
                record_type=row[3],
                value=row[4],
                unit=row[5],
                lab_name=row[6] if row[6] is not None else "self"
            ))

        return records
    
    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single health record by ID, with patient name resolved.

        Args:
            record_id: ID of the health record.

        Returns:
            Dict with id, timestamp, patient, record_type, value, unit, lab_name,
            created_at - or None if no record with this ID exists.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT hr.id, hr.timestamp, p.name, hr.record_type, hr.value,
                       hr.unit, hr.lab_name, hr.created_at
                FROM health_records hr
                INNER JOIN patients p ON hr.patient_id = p.id
                WHERE hr.id = ?
            """, (record_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return {
            "id": row[0],
            "timestamp": row[1],
            "patient": row[2],
            "record_type": row[3],
            "value": row[4],
            "unit": row[5],
            "lab_name": row[6] if row[6] is not None else "self",
            "created_at": row[7]
        }

    def update(
        self,
        record_id: int,
        value: Optional[str] = None,
        unit: Optional[str] = None,
        update_unit: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Update a health record's value and/or unit.

        Args:
            record_id: ID of the health record to update.
            value: New value, if being changed.
            unit: New unit, if update_unit is True (may be None to clear the unit).
            update_unit: Whether unit should be updated at all - distinguishes
                "not provided" from "explicitly set to null".

        Returns:
            The updated record (same shape as get_by_id), or None if no record
            with this ID exists.
        """
        set_clauses = []
        params: List[Any] = []
        if value is not None:
            set_clauses.append("value = ?")
            params.append(value)
        if update_unit:
            set_clauses.append("unit = ?")
            params.append(unit)

        if not set_clauses:
            return self.get_by_id(record_id)

        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"UPDATE health_records SET {', '.join(set_clauses)} WHERE id = ?",
                (*params, record_id)
            )
            if cursor.rowcount == 0:
                conn.commit()
                return None

            # Fetch the updated record within the same transaction, matching
            # the insert+select pattern used by save() to avoid a read/write race.
            cursor.execute("""
                SELECT hr.id, hr.timestamp, p.name, hr.record_type, hr.value,
                       hr.unit, hr.lab_name, hr.created_at
                FROM health_records hr
                INNER JOIN patients p ON hr.patient_id = p.id
                WHERE hr.id = ?
            """, (record_id,))
            row = cursor.fetchone()
            conn.commit()
        finally:
            conn.close()

        return {
            "id": row[0],
            "timestamp": row[1],
            "patient": row[2],
            "record_type": row[3],
            "value": row[4],
            "unit": row[5],
            "lab_name": row[6] if row[6] is not None else "self",
            "created_at": row[7]
        }

    def delete(self, record_id: int) -> bool:
        """
        Delete a health record by ID.

        Args:
            record_id: ID of the health record to delete.

        Returns:
            True if a record was deleted, False if no record with this ID existed.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM health_records WHERE id = ?", (record_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        finally:
            conn.close()

        return deleted

    def save_batch(
        self,
        patient_id: int,
        timestamp: datetime,
        lab_name: str,
        test_results: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Save multiple health records atomically (all or nothing).
        
        Args:
            patient_id: ID of the patient.
            timestamp: When the sample was collected (used for all records).
            lab_name: Name of the laboratory/hospital.
            test_results: List of test result dictionaries with keys:
                - test_name: Name of the test (maps to record_type).
                - results: Test result value (maps to value).
                - unit: Unit of measurement (maps to unit).
        
        Returns:
            List[int]: List of inserted record IDs.
        
        Raises:
            Exception: If database transaction fails.
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Prepare all records for batch insert
            record_ids = []
            # Format timestamp as ISO 8601 UTC string for storage
            timestamp_str = format_iso(timestamp)
            
            for test_result in test_results:
                cursor.execute("""
                    INSERT INTO health_records 
                    (timestamp, patient_id, record_type, value, unit, lab_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_str,
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
                f"Successfully saved {len(record_ids)} health records atomically"
            )
            
            return record_ids
            
        except Exception as e:
            # Rollback on any error
            conn.rollback()
            logger.error(
                f"Error saving health records: {str(e)}. Transaction rolled back."
            )
            raise
        finally:
            conn.close()

