"""
Service layer for health record operations.

This service contains business logic for health record management
and orchestrates calls to repositories.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from repositories import PatientRepository, HealthRecordRepository
from schemas import HealthRecordResponse


class HealthService:
    """Service layer for health record operations."""
    
    def __init__(
        self,
        patient_repository: Optional[PatientRepository] = None,
        health_record_repository: Optional[HealthRecordRepository] = None
    ):
        """
        Initialize the health service.
        
        Args:
            patient_repository: Optional PatientRepository instance.
            health_record_repository: Optional HealthRecordRepository instance.
        """
        self._patient_repo = patient_repository or PatientRepository()
        self._record_repo = health_record_repository or HealthRecordRepository()
    
    def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        value: str,
        unit: Optional[str] = None,
        lab_name: Optional[str] = "self"
    ) -> Dict[str, Any]:
        """
        Save a health record.
        
        Args:
            timestamp: When the measurement was taken.
            patient: Patient name.
            record_type: Type of health record.
            value: The measurement value.
            unit: Unit of measurement (optional).
            lab_name: Name of the lab (optional).
        
        Returns:
            Dict with 'success' bool and either 'record' (HealthRecordResponse) 
            or 'message' (error message).
        """
        try:
            # Get patient ID from name
            patient_id = self._patient_repo.get_id_by_name(patient)
            if patient_id is None:
                return {"success": False, "message": f"Patient '{patient}' not found in database"}
            
            # Save the record and get the created record in a single transaction,
            # avoiding race conditions when returning newly created records
            _, record_dict = self._record_repo.save(
                timestamp=timestamp,
                patient_id=patient_id,
                record_type=record_type,
                value=value,
                unit=unit,
                lab_name=lab_name
            )
            
            return {
                "success": True,
                "record": HealthRecordResponse(
                    timestamp=record_dict["timestamp"],
                    patient=record_dict["patient"],
                    record_type=record_dict["record_type"],
                    value=record_dict["value"],
                    unit=record_dict["unit"],
                    lab_name=record_dict["lab_name"]
                )
            }
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            return {"success": False, "message": f"Database error: {str(e)}"}
    
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
                timestamp=record.timestamp.isoformat(),
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
            timestamp: When the sample was collected.
            lab_name: Name of the laboratory/hospital.
            test_results: List of test result dictionaries.
        
        Returns:
            int: Number of records saved.
        
        Raises:
            ValueError: If patient is not found in database.
        """
        # Get patient ID from name
        patient_id = self._patient_repo.get_id_by_name(patient_name)
        if patient_id is None:
            raise ValueError(f"Patient '{patient_name}' not found in database")
        
        # Save records atomically
        record_ids = self._record_repo.save_batch(
            patient_id=patient_id,
            timestamp=timestamp,
            lab_name=lab_name,
            test_results=test_results
        )
        
        return len(record_ids)
