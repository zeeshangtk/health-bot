"""
Patients router - patient management endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from schemas import PatientCreate, PatientResponse
from services import PatientService
from core.auth import verify_api_key

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["Patients"],
    dependencies=[Depends(verify_api_key)],  # Require API key for all endpoints
)

# Initialize service
patient_service = PatientService()


@router.post(
    "",
    response_model=PatientResponse,
    status_code=201,
    summary="Create a new patient",
    description="Add a new patient to the system. Patient names must be unique. Returns the created patient with ID and timestamp."
)
async def create_patient(patient: PatientCreate):
    """
    Create a new patient.
    
    - **name**: Patient's full name (required, must be unique)
    
    Returns the created patient object with ID and creation timestamp.
    Raises 409 Conflict if a patient with the same name already exists.
    """
    result = patient_service.add_patient(patient.name)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result["patient"]


@router.get(
    "",
    response_model=List[PatientResponse],
    summary="List all patients",
    description="Retrieve all patients in the system, sorted alphabetically by name."
)
async def list_patients():
    """
    Get all patients, sorted alphabetically.
    
    Returns a list of all patients with their ID, name, and creation timestamp.
    The list is sorted alphabetically by patient name.
    """
    return patient_service.get_patients()
