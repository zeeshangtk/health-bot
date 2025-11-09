"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict


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


class ImageUploadResponse(BaseModel):
    """Schema for image upload response.
    
    Returns success status, stored filename, and a success message after image upload.
    Optionally includes task_id for tracking background processing tasks.
    """
    status: str = Field(..., description="Upload status", example="success")
    filename: str = Field(..., description="Unique filename of the stored image", example="a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg")
    message: str = Field(..., description="Success message", example="Image uploaded successfully")
    task_id: Optional[str] = Field(None, description="Celery task ID for background processing (optional)", example="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
                "message": "Image uploaded successfully",
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }


class TestResult(BaseModel):
    """Schema for a single test result in a laboratory report."""
    test_name: str = Field(..., description="Name of the test", example="Blood Urea")
    results: str = Field(..., description="Test result value", example="64.0")
    unit: str = Field(..., description="Unit of measurement", example="mg/dl")
    reference_range: str = Field(..., description="Normal reference range for the test", example="10.0-40.0")


class HospitalInfo(BaseModel):
    """Schema for hospital information in a medical report."""
    hospital_name: str = Field(..., description="Name of the hospital", example="VR John Doe")
    report_type: str = Field(..., description="Type of medical report", example="Laboratory Reports")


class PatientInfo(BaseModel):
    """Schema for patient information in a medical report."""
    patient_name: str = Field(..., description="Full name of the patient", example="Mrs Test Patient")
    patient_id: str = Field(..., description="Patient ID or registration number", example="ABB17985")
    age_sex: str = Field(..., description="Age and sex of the patient", example="63Y / FEMALE")
    sample_date: str = Field(..., description="Date and time when the sample was collected", example="08-11-2025 03:17 PM")
    referring_doctor_full_name_titles: str = Field(
        ...,
        description="Full name and qualifications of the referring doctor",
        example="DR. John Doe MBBS, MD GENERAL MEDICINE, DNB CARDIOLOGY"
    )


class MedicalInfo(BaseModel):
    """Schema for complete medical information extracted from a report.
    
    This structure represents the standardized format for medical report data,
    including hospital information, patient details, and biochemistry test results.
    """
    hospital_info: HospitalInfo = Field(..., description="Hospital information")
    patient_info: PatientInfo = Field(..., description="Patient information")
    biochemistry_results: Dict[str, List[TestResult]] = Field(
        ...,
        description="Dictionary of test categories and their results",
        example={
            "KIDNEY_FUNCTION_TEST": [
                {
                    "test_name": "Blood Urea",
                    "results": "64.0",
                    "unit": "mg/dl",
                    "reference_range": "10.0-40.0"
                }
            ]
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "hospital_info": {
                    "hospital_name": "VR John Doe",
                    "report_type": "Laboratory Reports"
                },
                "patient_info": {
                    "patient_name": "Mrs Test Patient",
                    "patient_id": "ABB17985",
                    "age_sex": "63Y / FEMALE",
                    "sample_date": "08-11-2025 03:17 PM",
                    "referring_doctor_full_name_titles": "DR. John Doe MBBS, MD GENERAL MEDICINE, DNB CARDIOLOGY"
                },
                "biochemistry_results": {
                    "KIDNEY_FUNCTION_TEST": [
                        {
                            "test_name": "Blood Urea",
                            "results": "64.0",
                            "unit": "mg/dl",
                            "reference_range": "10.0-40.0"
                        }
                    ]
                }
            }
        }

