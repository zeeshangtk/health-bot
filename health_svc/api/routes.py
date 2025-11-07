"""
FastAPI route definitions for Health Service API.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from api.schemas import (
    HealthRecordCreate,
    HealthRecordResponse,
    PatientCreate,
    PatientResponse
)
from services.health_service import HealthService
from services.patient_service import PatientService

router = APIRouter()

# Initialize services
health_service = HealthService()
patient_service = PatientService()


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Health Service API", "version": "1.0.0"}


# Patient Endpoints
@router.post("/api/v1/patients", response_model=PatientResponse, status_code=201)
async def create_patient(patient: PatientCreate):
    """Create a new patient."""
    result = patient_service.add_patient(patient.name)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result["patient"]


@router.get("/api/v1/patients", response_model=List[PatientResponse])
async def list_patients():
    """Get all patients, sorted alphabetically."""
    return patient_service.get_patients()


# Health Record Endpoints
@router.post("/api/v1/records", response_model=HealthRecordResponse, status_code=201)
async def create_record(record: HealthRecordCreate):
    """Create a new health record."""
    result = health_service.save_record(
        timestamp=record.timestamp,
        patient=record.patient,
        record_type=record.record_type,
        data_type=record.data_type,
        value=record.value
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result["record"]


@router.get("/api/v1/records", response_model=List[HealthRecordResponse])
async def list_records(
    patient: Optional[str] = Query(None, description="Filter by patient name"),
    record_type: Optional[str] = Query(None, description="Filter by record type"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results")
):
    """Get health records with optional filters."""
    records = health_service.get_records(
        patient=patient,
        record_type=record_type,
        limit=limit
    )
    return records

