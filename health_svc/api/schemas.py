"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class PatientCreate(BaseModel):
    """Schema for creating a new patient.
    
    This model is used when creating a new patient in the system.
    Patient names must be unique.
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Patient full name (must be unique)",
        example="John Doe"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe"
            }
        }


class PatientResponse(BaseModel):
    """Schema for patient response.
    
    Returns patient information including ID, name, and creation timestamp.
    """
    id: int = Field(..., description="Unique patient identifier", example=1)
    name: str = Field(..., description="Patient full name", example="John Doe")
    created_at: str = Field(..., description="ISO format timestamp when patient was created", example="2025-01-01 10:00:00")
    
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
    data_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Data type format (e.g., 'text', 'number', 'json')",
        example="text"
    )
    value: str = Field(
        ...,
        min_length=1,
        description="The actual measurement value (format depends on data_type)",
        example="120/80"
    )
    
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
    """Schema for health record response.
    
    Returns health record information including timestamp, patient, record type, and measurement value.
    """
    timestamp: str = Field(..., description="ISO format timestamp when the measurement was taken", example="2025-01-01T10:00:00")
    patient: str = Field(..., description="Patient name", example="John Doe")
    record_type: str = Field(..., description="Type of health record", example="BP")
    data_type: str = Field(..., description="Data type format", example="text")
    value: str = Field(..., description="The measurement value", example="120/80")
    
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


class ImageUploadResponse(BaseModel):
    """Schema for image upload response.
    
    Returns success status, stored filename, and a success message after image upload.
    """
    status: str = Field(..., description="Upload status", example="success")
    filename: str = Field(..., description="Unique filename of the stored image", example="a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg")
    message: str = Field(..., description="Success message", example="Image uploaded successfully")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
                "message": "Image uploaded successfully"
            }
        }

