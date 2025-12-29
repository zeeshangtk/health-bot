"""
Pydantic schemas for medical information extracted from reports.

This module contains the single source of truth for lab report data structures.
These schemas are used for:
- Gemini AI extraction validation (LabReport)
- API responses (MedicalInfo)
- Background task processing (TestResult, HospitalInfo, PatientInfo)
"""
from typing import List, Dict, Optional

from pydantic import BaseModel, Field


class TestResult(BaseModel):
    """Schema for a single test result in a laboratory report.
    
    Represents an individual test measurement with its value, unit, and reference range.
    The results field is a string to accommodate special characters like arrows (↑, ↓).
    """
    test_name: str = Field(
        ...,
        description="Name of the test",
        examples=["Blood Urea", "Random Blood Sugar"]
    )
    results: str = Field(
        ...,
        description="Test result value (may include special characters like ↑ or ↓)",
        examples=["64.0", "↑250.0"]
    )
    unit: str = Field(
        ...,
        description="Unit of measurement",
        examples=["mg/dl", "mMol/L"]
    )
    reference_range: str = Field(
        ...,
        description="Normal reference range for the test",
        examples=["10.0-40.0", "136.0-145.0"]
    )


class HospitalInfo(BaseModel):
    """Schema for hospital information in a medical report.
    
    Contains identifying information about the hospital and report type.
    """
    hospital_name: str = Field(
        ...,
        description="Name of the hospital",
        examples=["VR John Doe"]
    )
    report_type: str = Field(
        ...,
        description="Type of medical report",
        examples=["Laboratory Reports"]
    )


class PatientInfo(BaseModel):
    """Schema for patient information in a medical report.
    
    Contains demographic and identification information about the patient,
    including referring doctor details. Some fields are optional as they
    may not be present in all lab reports.
    """
    patient_name: str = Field(
        ...,
        description="Full name of the patient",
        examples=["Mrs Test Patient"]
    )
    patient_id: Optional[str] = Field(
        None,
        description="Patient ID or registration number",
        examples=["ABB17985"]
    )
    age_sex: Optional[str] = Field(
        None,
        description="Age and sex of the patient",
        examples=["63Y / FEMALE"]
    )
    sample_date: str = Field(
        ...,
        description="Date and time when the sample was collected",
        examples=["08-11-2025 03:17 PM"]
    )
    referring_doctor_full_name_titles: Optional[str] = Field(
        None,
        description="Full name and qualifications of the referring doctor",
        examples=["DR. John Doe MBBS, MD GENERAL MEDICINE, DNB CARDIOLOGY"]
    )


class LabReport(BaseModel):
    """Schema for a complete laboratory report (Gemini AI extraction format).
    
    This structure represents the format returned by Gemini AI when extracting
    data from lab report images. It uses a flat list of results rather than
    categorized results.
    """
    hospital_info: HospitalInfo = Field(..., description="Hospital information")
    patient_info: PatientInfo = Field(..., description="Patient information")
    results: List[TestResult] = Field(..., description="List of test results")


class MedicalInfo(BaseModel):
    """Schema for complete medical information (API response format).
    
    This structure represents the standardized format for medical report data
    with categorized biochemistry results, used for API responses.
    """
    hospital_info: HospitalInfo = Field(..., description="Hospital information")
    patient_info: PatientInfo = Field(..., description="Patient information")
    biochemistry_results: Dict[str, List[TestResult]] = Field(
        ...,
        description="Dictionary of test categories and their results",
        examples=[{
            "KIDNEY_FUNCTION_TEST": [
                {
                    "test_name": "Blood Urea",
                    "results": "64.0",
                    "unit": "mg/dl",
                    "reference_range": "10.0-40.0"
                }
            ]
        }]
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
