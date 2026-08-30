"""
Pydantic schemas for API request/response validation.

This module contains all Pydantic models used at API boundaries.
"""
from schemas.patient import PatientCreate, PatientResponse
from schemas.health_record import (
    HealthRecordCreate,
    HealthRecordResponse,
    HealthRecordUpdate,
)
from schemas.upload import ImageUploadResponse, UploadStatusResponse
from schemas.medical_info import (
    TestResult,
    HospitalInfo,
    PatientInfo,
    LabReport,
    MedicalInfo,
)

__all__ = [
    # Patient schemas
    "PatientCreate",
    "PatientResponse",
    # Health record schemas
    "HealthRecordCreate",
    "HealthRecordResponse",
    "HealthRecordUpdate",
    # Upload schemas
    "ImageUploadResponse",
    "UploadStatusResponse",
    # Medical info schemas
    "TestResult",
    "HospitalInfo",
    "PatientInfo",
    "LabReport",
    "MedicalInfo",
]

