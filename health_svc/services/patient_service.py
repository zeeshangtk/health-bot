"""
Service layer for patient operations.
"""
from typing import List, Dict, Any, Optional
from storage.database import Database, get_database
from api.schemas import PatientResponse


class PatientService:
    """Service layer for patient operations."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
    
    def add_patient(self, name: str) -> Dict[str, Any]:
        """
        Add a new patient.
        
        Returns:
            Dict with 'success' bool and either 'patient' (PatientResponse) 
            or 'message' (error message)
        """
        success = self.db.add_patient(name)
        
        if success:
            # Fetch the created patient
            patients = self.db.get_patients()
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
        """Get all patients."""
        patients = self.db.get_patients()
        return [
            PatientResponse(
                id=p["id"],
                name=p["name"],
                created_at=p["created_at"]
            )
            for p in patients
        ]

