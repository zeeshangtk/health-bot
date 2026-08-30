"""
Service layer for health record operations.

This service contains business logic for health record management
and orchestrates calls to repositories.

Architecture:
    API Layer (routers) → HealthService → Repositories → Database

Dependency Injection:
    HealthService receives its repositories via constructor injection.
    Use core.dependencies.get_health_service() in routers with Depends().
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from repositories import PatientRepository, HealthRecordRepository
from schemas import HealthRecordResponse
from core.exceptions import PatientNotFoundError, DatabaseError
from core.datetime_utils import to_utc, format_iso

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service layer for health record operations.
    
    Handles business logic for health record management including
    validation, patient lookup, and coordination with repositories.
    """
    
    def __init__(
        self,
        patient_repository: PatientRepository,
        health_record_repository: HealthRecordRepository
    ):
        """
        Initialize the health service.
        
        Args:
            patient_repository: PatientRepository instance for patient lookups.
            health_record_repository: HealthRecordRepository instance for record operations.
                                      Both are injected via core.dependencies.get_health_service().
        """
        self._patient_repo = patient_repository
        self._record_repo = health_record_repository
    
    def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        value: str,
        unit: Optional[str] = None,
        lab_name: Optional[str] = "self"
    ) -> HealthRecordResponse:
        """
        Save a health record.
        
        Args:
            timestamp: When the measurement was taken (will be normalized to UTC).
            patient: Patient name.
            record_type: Type of health record.
            value: The measurement value.
            unit: Unit of measurement (optional).
            lab_name: Name of the lab (optional, defaults to "self").
        
        Returns:
            HealthRecordResponse: The created health record.
        
        Raises:
            PatientNotFoundError: If the patient doesn't exist.
            DatabaseError: If a database error occurs.
        """
        logger.info(f"Saving health record for patient: {patient}, type: {record_type}")
        
        # Get patient ID from name
        patient_id = self._patient_repo.get_id_by_name(patient)
        if patient_id is None:
            logger.warning(f"Patient not found: {patient}")
            raise PatientNotFoundError(patient_name=patient)
        
        try:
            # Normalize timestamp to UTC
            utc_timestamp = to_utc(timestamp)
            
            # Save the record and get the created record in a single transaction
            _, record_dict = self._record_repo.save(
                timestamp=utc_timestamp,
                patient_id=patient_id,
                record_type=record_type,
                value=value,
                unit=unit,
                lab_name=lab_name
            )
            
            logger.info(f"Health record saved successfully for patient: {patient}")
            return HealthRecordResponse(
                timestamp=record_dict["timestamp"],
                patient=record_dict["patient"],
                record_type=record_dict["record_type"],
                value=record_dict["value"],
                unit=record_dict["unit"],
                lab_name=record_dict["lab_name"]
            )
        except Exception as e:
            logger.error(f"Database error saving health record: {e}", exc_info=True)
            raise DatabaseError(operation="save_record") from e
    
    def get_records(
        self,
        patient: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[HealthRecordResponse]:
        """
        Get health records with filters.
        
        Args:
            patient: Filter by patient name (optional).
            record_type: Filter by record type (optional).
            limit: Maximum number of records to return (optional).
        
        Returns:
            List of HealthRecordResponse objects.
        """
        records = self._record_repo.get_all(
            patient_name=patient,
            record_type=record_type,
            limit=limit
        )
        
        return [
            HealthRecordResponse(
                timestamp=format_iso(record.timestamp),
                patient=record.patient,
                record_type=record.record_type,
                value=record.value,
                unit=record.unit,
                lab_name=record.lab_name
            )
            for record in records
        ]
    
    def save_lab_report_records(
        self,
        patient_name: str,
        timestamp: datetime,
        lab_name: str,
        test_results: List[Dict[str, Any]]
    ) -> int:
        """
        Save multiple health records from a lab report atomically.
        
        Args:
            patient_name: Name of the patient.
            timestamp: When the sample was collected (will be normalized to UTC).
            lab_name: Name of the laboratory/hospital.
            test_results: List of test result dictionaries with keys:
                         test_name, results, unit (optional).
        
        Returns:
            int: Number of records saved.
        
        Raises:
            PatientNotFoundError: If patient is not found in database.
            DatabaseError: If a database error occurs.
        """
        logger.info(f"Saving {len(test_results)} lab report records for patient: {patient_name}")
        
        # Get patient ID from name
        patient_id = self._patient_repo.get_id_by_name(patient_name)
        if patient_id is None:
            logger.warning(f"Patient not found: {patient_name}")
            raise PatientNotFoundError(patient_name=patient_name)
        
        try:
            # Normalize timestamp to UTC
            utc_timestamp = to_utc(timestamp)
            
            # Save records atomically
            record_ids = self._record_repo.save_batch(
                patient_id=patient_id,
                timestamp=utc_timestamp,
                lab_name=lab_name,
                test_results=test_results
            )
            
            logger.info(f"Saved {len(record_ids)} records for patient: {patient_name}")
            return len(record_ids)
        except Exception as e:
            logger.error(f"Database error saving lab report records: {e}", exc_info=True)
            raise DatabaseError(operation="save_lab_report_records") from e
