"""
Pydantic schemas for patient-related API operations.
"""
from pydantic import BaseModel, Field


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

