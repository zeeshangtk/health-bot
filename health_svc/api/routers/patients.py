"""
Patients router - patient management endpoints.

This router handles patient CRUD operations via RESTful endpoints.
All endpoints require API key authentication.

Architecture:
    HTTP Request → Router (this file) → PatientService → PatientRepository → Database

Safety Features:
    - Default query limits to prevent unbounded queries
    - Warnings logged when limits are applied

Dependency Injection:
    Services are injected via FastAPI's Depends() mechanism.
    The DI chain is defined in core/dependencies.py.
"""
import logging
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

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
# SAFE DEFAULTS
# =============================================================================
# These constants define safe defaults for query parameters.
# Prevents unbounded queries on resource-constrained systems.

DEFAULT_QUERY_LIMIT = 100  # Default limit if none specified
MAX_QUERY_LIMIT = 500      # Maximum allowed limit (patients are fewer than records)


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
    
    Returns the created patient object with ID and creation timestamp (UTC).
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
    description=f"Retrieve all patients in the system, sorted alphabetically by name. "
                f"Default limit is {DEFAULT_QUERY_LIMIT}, maximum is {MAX_QUERY_LIMIT}."
)
async def list_patients(
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=MAX_QUERY_LIMIT,
        description=f"Maximum number of patients to return (1-{MAX_QUERY_LIMIT}). "
                    f"Defaults to {DEFAULT_QUERY_LIMIT} if not specified.",
        example=50
    ),
    patient_service: PatientService = Depends(get_patient_service)
):
    """
    Get all patients, sorted alphabetically.
    
    Query Parameters:
    - **limit**: Maximum number of patients to return (optional, 1-500, defaults to 100)
    
    Returns a list of all patients with their ID, name, and creation timestamp.
    The list is sorted alphabetically by patient name.
    
    Safe Defaults:
    - If no limit is specified, applies default of 100 to prevent unbounded queries
    - Logs a warning when default limit is applied
    """
    # Apply safe default limit if not specified
    effective_limit = limit
    if effective_limit is None:
        effective_limit = DEFAULT_QUERY_LIMIT
        logger.warning(
            "No limit specified for patient list, applying default",
            extra={"default_limit": DEFAULT_QUERY_LIMIT}
        )
    
    # Get all patients and apply limit
    all_patients = patient_service.get_patients()
    return all_patients[:effective_limit]
