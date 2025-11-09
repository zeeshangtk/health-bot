"""
FastAPI route definitions for Health Service API.
"""
import logging
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import Optional, List

from api.schemas import (
    HealthRecordCreate,
    HealthRecordResponse,
    PatientCreate,
    PatientResponse,
    ImageUploadResponse
)
from services.health_service import HealthService
from services.patient_service import PatientService
from services.upload_service import UploadService

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
health_service = HealthService()
patient_service = PatientService()
upload_service = UploadService()


@router.get("/", tags=["Health"])
async def root():
    """
    Root endpoint.
    
    Returns basic API information including service name and version.
    Use this endpoint to verify the API is running and accessible.
    """
    return {"message": "Health Service API", "version": "1.0.0"}


# Patient Endpoints
@router.post(
    "/api/v1/patients",
    response_model=PatientResponse,
    status_code=201,
    tags=["Patients"],
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
    "/api/v1/patients",
    response_model=List[PatientResponse],
    tags=["Patients"],
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


# Health Record Endpoints
@router.post(
    "/api/v1/records",
    response_model=HealthRecordResponse,
    status_code=201,
    tags=["Health Records"],
    summary="Create a new health record",
    description="Add a new health measurement record for a patient. Supports various record types like blood pressure, weight, temperature, etc."
)
async def create_record(record: HealthRecordCreate):
    """
    Create a new health record.
    
    - **timestamp**: ISO format datetime when the measurement was taken
    - **patient**: Patient name (must exist in the system)
    - **record_type**: Type of measurement (e.g., 'BP', 'Weight', 'Temperature')
    - **data_type**: Format of the data (e.g., 'text', 'number', 'json')
    - **value**: The actual measurement value
    
    Returns the created health record.
    Raises 400 Bad Request if the patient doesn't exist or validation fails.
    """
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


@router.get(
    "/api/v1/records",
    response_model=List[HealthRecordResponse],
    tags=["Health Records"],
    summary="List health records",
    description="Retrieve health records with optional filtering by patient name, record type, and result limit."
)
async def list_records(
    patient: Optional[str] = Query(None, description="Filter by patient name (exact match)", example="John Doe"),
    record_type: Optional[str] = Query(None, description="Filter by record type (e.g., 'BP', 'Weight')", example="BP"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of records to return (1-1000)", example=10)
):
    """
    Get health records with optional filters.
    
    Query Parameters:
    - **patient**: Filter records by patient name (optional, exact match)
    - **record_type**: Filter records by type (optional, e.g., 'BP', 'Weight', 'Temperature')
    - **limit**: Maximum number of records to return (optional, 1-1000)
    
    Returns a list of health records matching the filters.
    If no filters are provided, returns all records (up to the limit if specified).
    """
    records = health_service.get_records(
        patient=patient,
        record_type=record_type,
        limit=limit
    )
    return records


# Image Upload Endpoint
@router.post(
    "/api/v1/records/upload",
    response_model=ImageUploadResponse,
    status_code=201,
    tags=["Health Records"],
    summary="Upload an image file",
    description="Upload a single image file (JPEG, PNG, GIF, or BMP) via multipart/form-data. "
                "The image will be stored in the uploads directory with a unique filename. "
                "Maximum file size is 10MB."
)
async def upload_image(file: UploadFile = File(..., description="Image file to upload (JPEG, PNG, GIF, or BMP)")):
    """
    Upload an image file.
    
    - **file**: Image file to upload (required, must be JPEG, PNG, GIF, or BMP format)
    
    The uploaded file will be stored in the uploads directory with a unique UUID-based filename
    to avoid conflicts. The original file extension is preserved.
    
    Returns the stored filename and success message.
    
    Raises:
    - 400 Bad Request: If no file is uploaded, file is not an image, or file size exceeds 10MB
    - 413 Payload Too Large: If the file size exceeds the maximum allowed size
    - 415 Unsupported Media Type: If the upload is not multipart/form-data
    - 500 Internal Server Error: For file system write failures
    """
    unique_filename, file_path, task_id = await upload_service.save_uploaded_file(file)
    
    return ImageUploadResponse(
        status="success",
        filename=unique_filename,
        message="Image uploaded successfully",
        task_id=task_id
    )

