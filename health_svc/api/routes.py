"""
FastAPI route definitions for Health Service API.
"""
import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, status
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
from config import UPLOAD_DIR, UPLOAD_MAX_SIZE

# Configure logging
logger = logging.getLogger(__name__)

# Allowed image MIME types and extensions
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/bmp": [".bmp"]
}
ALLOWED_EXTENSIONS = {ext for exts in ALLOWED_IMAGE_TYPES.values() for ext in exts}

router = APIRouter()

# Initialize services
health_service = HealthService()
patient_service = PatientService()


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
    # Validate file is provided
    if not file:
        logger.error("No file provided in upload request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Validate content type
    if not file.content_type:
        logger.error("File has no content type")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content type is missing"
        )
    
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        logger.error(f"Invalid content type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}"
        )
    
    # Validate file extension
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""
    if not file_extension or file_extension not in ALLOWED_EXTENSIONS:
        logger.error(f"Invalid file extension: {file_extension}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    # Verify extension matches content type
    expected_extensions = ALLOWED_IMAGE_TYPES.get(file.content_type, [])
    if file_extension not in expected_extensions:
        logger.error(f"File extension {file_extension} does not match content type {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File extension does not match content type"
        )
    
    try:
        # Read file content to check size and validate
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size == 0:
            logger.error("Empty file uploaded")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        if file_size > UPLOAD_MAX_SIZE:
            logger.error(f"File size {file_size} exceeds maximum {UPLOAD_MAX_SIZE}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {UPLOAD_MAX_SIZE / (1024 * 1024):.1f}MB"
            )
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}{file_extension}"
        upload_path = Path(UPLOAD_DIR) / unique_filename
        
        # Ensure upload directory exists (should already exist from config, but double-check)
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file to disk
        try:
            with open(upload_path, "wb") as f:
                f.write(file_content)
            logger.info(f"Successfully uploaded file: {unique_filename} (size: {file_size} bytes)")
        except OSError as e:
            logger.error(f"Failed to write file to disk: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file to disk"
            )
        
        return ImageUploadResponse(
            status="success",
            filename=unique_filename,
            message="Image uploaded successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the upload"
        )

