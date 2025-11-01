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
        data_type: str,
        value: str
    ):
        """
        Initialize a health record.
        
        Args:
            timestamp: When the record was created
            patient: Name of the patient
            record_type: Type of record (BP, Sugar, Creatinine, Weight, Other)
            data_type: Type of data (e.g., "text", "number", "reading")
            value: The recorded value (as string to support various formats)
        """
        self.timestamp = timestamp
        self.patient = patient
        self.record_type = record_type
        self.data_type = data_type
        self.value = value
    
    def to_dict(self) -> dict:
        """Convert record to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "patient": self.patient,
            "record_type": self.record_type,
            "data_type": self.data_type,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HealthRecord':
        """Create record from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            patient=data["patient"],
            record_type=data["record_type"],
            data_type=data["data_type"],
            value=data["value"]
        )
