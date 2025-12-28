"""
Pydantic schemas for medical information extracted from reports.
"""
from typing import List, Dict

from pydantic import BaseModel, Field


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

