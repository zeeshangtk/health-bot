"""
Patients router - patient management endpoints.

This router handles patient CRUD operations via RESTful endpoints.
All endpoints require API key authentication.

Architecture:
    HTTP Request → Router (this file) → PatientService → PatientRepository → Database

Dependency Injection:
    Services are injected via FastAPI's Depends() mechanism.
    The DI chain is defined in core/dependencies.py.
"""
import logging
from fastapi import APIRouter, Depends
from typing import List

from schemas import PatientCreate, PatientResponse
from services import PatientService
from core.auth import verify_api_key
from core.dependencies import get_patient_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["Patients"],
    dependencies=[Depends(verify_api_key)],  # Require API key for all endpoints
)


# =============================================================================
# ENDPOINTS
# =============================================================================
# Note: Services are injected via Depends(). No module-level instantiation.
# This enables proper testing via dependency_overrides and ensures clean layering.

@router.post(
    "",
    response_model=PatientResponse,
    status_code=201,
    summary="Create a new patient",
    description="Add a new patient to the system. Patient names must be unique. Returns the created patient with ID and timestamp."
)
async def create_patient(
    patient: PatientCreate,
    patient_service: PatientService = Depends(get_patient_service)
):
    """
    Create a new patient.
    
    - **name**: Patient's full name (required, must be unique)
    
    Returns the created patient object with ID and creation timestamp.
    Raises 409 Conflict if a patient with the same name already exists.
    
    Note: DuplicatePatientError is raised by the service and handled
    by the exception handler registered in main.py.
    """
    # Service raises DuplicatePatientError if patient exists
    # Exception is handled by setup_exception_handlers()
    return patient_service.add_patient(patient.name)


@router.get(
    "",
    response_model=List[PatientResponse],
    summary="List all patients",
    description="Retrieve all patients in the system, sorted alphabetically by name."
)
async def list_patients(
    patient_service: PatientService = Depends(get_patient_service)
):
    """
    Get all patients, sorted alphabetically.
    
    Returns a list of all patients with their ID, name, and creation timestamp.
    The list is sorted alphabetically by patient name.
    """
    return patient_service.get_patients()
