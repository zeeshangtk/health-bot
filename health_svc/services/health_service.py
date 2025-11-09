"""
Service layer for health record operations.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from storage.database import Database, get_database
from storage.models import HealthRecord
from api.schemas import HealthRecordResponse


class HealthService:
    """Service layer for health record operations."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
    
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
        
        Returns:
            Dict with 'success' bool and either 'record' (HealthRecordResponse) 
            or 'message' (error message)
        """
        try:
            record_id = self.db.save_record(
                timestamp=timestamp,
                patient=patient,
                record_type=record_type,
                value=value,
                unit=unit,
                lab_name=lab_name
            )
            
            # Fetch the saved record to return full details
            # Get the most recent record for this patient (should be the one we just saved)
            records = self.db.get_records(patient=patient, limit=1)
            if records:
                record = records[0]
                return {
                    "success": True,
                    "record": HealthRecordResponse(
                        timestamp=record.timestamp.isoformat(),
                        patient=record.patient,
                        record_type=record.record_type,
                        value=record.value,
                        unit=record.unit,
                        lab_name=record.lab_name
                    )
                }
            else:
                return {
                    "success": False,
                    "message": "Record saved but could not be retrieved"
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
        """Get health records with filters."""
        records = self.db.get_records(
            patient=patient,
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

