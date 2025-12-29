"""
Service layer for patient operations.

This service contains business logic for patient management
and orchestrates calls to repositories.

Architecture:
    API Layer (routers) → PatientService → PatientRepository → Database

Dependency Injection:
    PatientService receives its repository via constructor injection.
    Use core.dependencies.get_patient_service() in routers with Depends().
"""
import logging
from typing import List, Optional

from repositories import PatientRepository
from schemas import PatientResponse
from core.exceptions import PatientNotFoundError, DuplicatePatientError

logger = logging.getLogger(__name__)


class PatientService:
    """
    Service layer for patient operations.
    
    Handles business logic for patient management including validation,
    error handling, and coordination with the repository layer.
    """
    
    def __init__(self, patient_repository: PatientRepository):
        """
        Initialize the patient service.
        
        Args:
            patient_repository: PatientRepository instance for data access.
                               Injected via core.dependencies.get_patient_service().
        """
        self._repo = patient_repository
    
    def add_patient(self, name: str) -> PatientResponse:
        """
        Add a new patient.
        
        Args:
            name: Patient's full name.
        
        Returns:
            PatientResponse: The created patient.
        
        Raises:
            DuplicatePatientError: If a patient with this name already exists.
        """
        logger.info(f"Adding new patient: {name}")
        
        # Repository returns None if patient already exists (UNIQUE constraint)
        created_patient = self._repo.add(name)
        
        if created_patient is None:
            logger.warning(f"Patient already exists: {name}")
            raise DuplicatePatientError(patient_name=name)
        
        logger.info(f"Patient created successfully: {name} (id={created_patient['id']})")
        return PatientResponse(
            id=created_patient["id"],
            name=created_patient["name"],
            created_at=created_patient["created_at"]
        )
    
    def get_patients(self) -> List[PatientResponse]:
        """
        Get all patients.
        
        Returns:
            List of PatientResponse objects, sorted alphabetically by name.
        """
        patients = self._repo.get_all()
        return [
            PatientResponse(
                id=p["id"],
                name=p["name"],
                created_at=p["created_at"]
            )
            for p in patients
        ]
    
    def get_patient_by_name(self, name: str) -> PatientResponse:
        """
        Get a patient by name.
        
        Args:
            name: Patient's name.
        
        Returns:
            PatientResponse: The patient data.
        
        Raises:
            PatientNotFoundError: If no patient with this name exists.
        """
        patient = self._repo.get_by_name(name)
        if patient is None:
            raise PatientNotFoundError(patient_name=name)
        
        return PatientResponse(
            id=patient["id"],
            name=patient["name"],
            created_at=patient["created_at"]
        )
    
    def get_patient_by_name_or_none(self, name: str) -> Optional[PatientResponse]:
        """
        Get a patient by name, returning None if not found.
        
        This is a convenience method for cases where missing patients
        should not raise an exception (e.g., optional filtering).
        
        Args:
            name: Patient's name.
        
        Returns:
            PatientResponse or None if not found.
        """
        patient = self._repo.get_by_name(name)
        if patient:
            return PatientResponse(
                id=patient["id"],
                name=patient["name"],
                created_at=patient["created_at"]
            )
        return None
