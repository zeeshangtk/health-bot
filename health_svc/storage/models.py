"""
Data models for health records.
"""
from datetime import datetime
from typing import Optional


class HealthRecord:
    """Model representing a health measurement record."""
    
    def __init__(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        value: str,
        unit: Optional[str] = None,
        lab_name: Optional[str] = "self"
    ):
        """
        Initialize a health record.
        
        Args:
            timestamp: When the record was created
            patient: Name of the patient
            record_type: Type of record (BP, Sugar, Creatinine, Weight, Other)
            value: The recorded value (as string to support various formats)
            unit: Unit of measurement (optional)
            lab_name: Name of the lab (optional, defaults to "self")
        """
        self.timestamp = timestamp
        self.patient = patient
        self.record_type = record_type
        self.value = value
        self.unit = unit
        self.lab_name = lab_name
    
    def to_dict(self) -> dict:
        """Convert record to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "patient": self.patient,
            "record_type": self.record_type,
            "value": self.value,
            "unit": self.unit,
            "lab_name": self.lab_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HealthRecord':
        """Create record from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            patient=data["patient"],
            record_type=data["record_type"],
            value=data["value"],
            unit=data.get("unit"),
            lab_name=data.get("lab_name", "self")
        )

