"""
Service layer for patient operations.

This service contains business logic for patient management
and orchestrates calls to repositories.
"""
from typing import List, Dict, Any, Optional

from repositories import PatientRepository
from schemas import PatientResponse


class PatientService:
    """Service layer for patient operations."""
    
    def __init__(self, patient_repository: Optional[PatientRepository] = None):
        """
        Initialize the patient service.
        
        Args:
            patient_repository: Optional PatientRepository instance.
        """
        self._repo = patient_repository or PatientRepository()
    
    def add_patient(self, name: str) -> Dict[str, Any]:
        """
        Add a new patient.
        
        Args:
            name: Patient's full name.
        
        Returns:
            Dict with 'success' bool and either 'patient' (PatientResponse) 
            or 'message' (error message).
        """
        success = self._repo.add(name)
        
        if success:
            # Fetch the created patient
            patients = self._repo.get_all()
            created_patient = next((p for p in patients if p["name"] == name), None)
            
            if created_patient:
                return {
                    "success": True,
                    "patient": PatientResponse(
                        id=created_patient["id"],
                        name=created_patient["name"],
                        created_at=created_patient["created_at"]
                    )
                }
            else:
                return {
                    "success": False,
                    "message": "Patient created but could not be retrieved"
                }
        else:
            return {
                "success": False,
                "message": f"Patient '{name}' already exists"
            }
    
    def get_patients(self) -> List[PatientResponse]:
        """
        Get all patients.
        
        Returns:
            List of PatientResponse objects.
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
    
    def get_patient_by_name(self, name: str) -> Optional[PatientResponse]:
        """
        Get a patient by name.
        
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
