"""
Pydantic schemas for health record-related API operations.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthRecordCreate(BaseModel):
    """Schema for creating a new health record.
    
    Used to record various health measurements such as blood pressure, weight, temperature, etc.
    The patient must exist in the system before creating a record.
    """
    timestamp: datetime = Field(
        ...,
        description="ISO format datetime when the measurement was taken",
        example="2025-01-01T10:00:00"
    )
    patient: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Patient name (must match an existing patient)",
        example="John Doe"
    )
    record_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of health record (e.g., 'BP' for blood pressure, 'Weight', 'Temperature')",
        example="BP"
    )
    value: str = Field(
        ...,
        min_length=1,
        description="The actual measurement value",
        example="120/80"
    )
    unit: Optional[str] = Field(
        None,
        max_length=50,
        description="Unit of measurement (e.g., 'mg/dl', 'mmHg', 'kg')",
        example="mmHg"
    )
    lab_name: Optional[str] = Field(
        "self",
        max_length=200,
        description="Name of the laboratory or facility where the test was performed (defaults to 'self')",
        example="City Lab"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-01T10:00:00",
                "patient": "John Doe",
                "record_type": "BP",
                "value": "120/80",
                "unit": "mmHg",
                "lab_name": "City Lab"
            }
        }


class HealthRecordResponse(BaseModel):
    """Schema for health record response.
    
    Returns health record information including timestamp, patient, record type, and measurement value.
    """
    timestamp: str = Field(..., description="ISO format timestamp when the measurement was taken", example="2025-01-01T10:00:00")
    patient: str = Field(..., description="Patient name", example="John Doe")
    record_type: str = Field(..., description="Type of health record", example="BP")
    value: str = Field(..., description="The measurement value", example="120/80")
    unit: Optional[str] = Field(None, description="Unit of measurement", example="mmHg")
    lab_name: Optional[str] = Field("self", description="Name of the laboratory or facility (defaults to 'self')", example="City Lab")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-01T10:00:00",
                "patient": "John Doe",
                "record_type": "BP",
                "value": "120/80",
                "unit": "mmHg",
                "lab_name": "City Lab"
            }
        }

