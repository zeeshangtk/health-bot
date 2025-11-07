"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""
    name: str = Field(..., min_length=1, max_length=200, description="Patient full name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe"
            }
        }


class PatientResponse(BaseModel):
    """Schema for patient response."""
    id: int
    name: str
    created_at: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "created_at": "2025-01-01 10:00:00"
            }
        }


class HealthRecordCreate(BaseModel):
    """Schema for creating a new health record."""
    timestamp: datetime
    patient: str = Field(..., min_length=1, max_length=200)
    record_type: str = Field(..., min_length=1, max_length=50)
    data_type: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-01T10:00:00",
                "patient": "John Doe",
                "record_type": "BP",
                "data_type": "text",
                "value": "120/80"
            }
        }


class HealthRecordResponse(BaseModel):
    """Schema for health record response."""
    timestamp: str  # ISO format string
    patient: str
    record_type: str
    data_type: str
    value: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-01T10:00:00",
                "patient": "John Doe",
                "record_type": "BP",
                "data_type": "text",
                "value": "120/80"
            }
        }

