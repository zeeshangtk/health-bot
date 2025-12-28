"""
Pydantic schemas for API request/response validation.

This module contains all Pydantic models used at API boundaries.
"""
from schemas.patient import PatientCreate, PatientResponse
from schemas.health_record import (
    HealthRecordCreate,
    HealthRecordResponse,
)
from schemas.upload import ImageUploadResponse
from schemas.medical_info import (
    TestResult,
    HospitalInfo,
    PatientInfo,
    MedicalInfo,
)

__all__ = [
    # Patient schemas
    "PatientCreate",
    "PatientResponse",
    # Health record schemas
    "HealthRecordCreate",
    "HealthRecordResponse",
    # Upload schemas
    "ImageUploadResponse",
    # Medical info schemas
    "TestResult",
    "HospitalInfo",
    "PatientInfo",
    "MedicalInfo",
]

