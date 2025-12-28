"""
Records router - health record and image upload endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Response, Form
from typing import Optional, List

from schemas import (
    HealthRecordCreate,
    HealthRecordResponse,
    ImageUploadResponse
)
from services import HealthService, UploadService
from services.graph import GraphService

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/records", tags=["Health Records"])

# Initialize services
health_service = HealthService()
upload_service = UploadService()
graph_service = GraphService()


@router.post(
    "",
    response_model=HealthRecordResponse,
    status_code=201,
    summary="Create a new health record",
    description="Add a new health measurement record for a patient. Supports various record types like blood pressure, weight, temperature, etc."
)
async def create_record(record: HealthRecordCreate):
    """
    Create a new health record.
    
    - **timestamp**: ISO format datetime when the measurement was taken
    - **patient**: Patient name (must exist in the system)
    - **record_type**: Type of measurement (e.g., 'BP', 'Weight', 'Temperature')
    - **value**: The actual measurement value
    - **unit**: Unit of measurement (optional, e.g., 'mg/dl', 'mmHg', 'kg')
    - **lab_name**: Name of the laboratory or facility (optional)
    
    Returns the created health record.
    Raises 400 Bad Request if the patient doesn't exist or validation fails.
    """
    result = health_service.save_record(
        timestamp=record.timestamp,
        patient=record.patient,
        record_type=record.record_type,
        value=record.value,
        unit=record.unit,
        lab_name=record.lab_name
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result["record"]


@router.get(
    "",
    response_model=List[HealthRecordResponse],
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


@router.get(
    "/html-view",
    summary="Get HTML graph view of patient health records",
    description="Generate an interactive HTML graph visualization of a patient's health records using Plotly. "
                "The graph displays all record types (e.g., Sugar, Creatinine, BP) with timestamps on x-axis and values on y-axis."
)
async def get_html_view(
    patient_name: str = Query(..., description="Patient name to generate graph for", example="John Doe")
):
    """
    Get HTML graph view of patient health records.
    
    Query Parameters:
    - **patient_name**: Patient name to generate graph for (required)
    
    Returns an HTML page containing an interactive Plotly graph showing:
    - X-axis: Timestamp of measurements
    - Y-axis: Measurement values
    - Multiple traces: One for each record type (Sugar, Creatinine, BP, etc.)
    
    The HTML can be consumed by the Telegram bot or viewed directly in a browser.
    
    Raises:
    - 400 Bad Request: If patient_name is not provided
    - 404 Not Found: If patient has no records (returns empty graph)
    """
    # Get records for the patient
    records = health_service.get_records(patient=patient_name)
    
    # Generate HTML graph
    html_content = graph_service.generate_html_graph(records, patient_name)
    
    # Return HTML response
    return Response(content=html_content, media_type="text/html")


@router.post(
    "/upload",
    response_model=ImageUploadResponse,
    status_code=201,
    summary="Upload an image file",
    description="Upload a single image file (JPEG, PNG, GIF, or BMP) via multipart/form-data. "
                "The image will be stored in the uploads directory with a unique filename. "
                "Maximum file size is 10MB."
)
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload (JPEG, PNG, GIF, or BMP)"),
    patient: Optional[str] = Form(None, description="Patient name associated with the lab report")
):
    """
    Upload an image file.
    
    - **file**: Image file to upload (required, must be JPEG, PNG, GIF, or BMP format)
    - **patient**: Optional patient name to associate with the record
    
    The uploaded file will be stored in the uploads directory with a unique UUID-based filename
    to avoid conflicts. The original file extension is preserved.
    
    Returns the stored filename and success message.
    
    Raises:
    - 400 Bad Request: If no file is uploaded, file is not an image, or file size exceeds 10MB
    - 413 Payload Too Large: If the file size exceeds the maximum allowed size
    - 415 Unsupported Media Type: If the upload is not multipart/form-data
    - 500 Internal Server Error: For file system write failures
    """
    unique_filename, file_path, task_id = await upload_service.save_uploaded_file(file, patient_name=patient)
    
    return ImageUploadResponse(
        status="success",
        filename=unique_filename,
        message="Image uploaded successfully",
        task_id=task_id
    )
