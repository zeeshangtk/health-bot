"""
Celery tasks for file upload processing.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from celery_app import celery_app
from storage.database import get_database
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


# Pydantic models for lab report structure
class TestResult(BaseModel):
    """Schema for a single test result in a laboratory report.
    
    Represents an individual test measurement with its value, unit, and reference range.
    The results field is a string to accommodate special characters like arrows (↑, ↓).
    """
    test_name: str = Field(..., description="Name of the test", examples=["Blood Urea", "Random Blood Sugar"])
    results: str = Field(..., description="Test result value (may include special characters like ↑ or ↓)", examples=["64.0", "↑250.0"])
    unit: str = Field(..., description="Unit of measurement", examples=["mg/dl", "mMol/L"])
    reference_range: str = Field(..., description="Normal reference range for the test", examples=["10.0-40.0", "136.0-145.0"])


class HospitalInfo(BaseModel):
    """Schema for hospital information in a medical report.
    
    Contains identifying information about the hospital and report type.
    """
    hospital_name: str = Field(..., description="Name of the hospital", examples=["VR John Doe"])
    report_type: str = Field(..., description="Type of medical report", examples=["Laboratory Reports"])


class PatientInfo(BaseModel):
    """Schema for patient information in a medical report.
    
    Contains demographic and identification information about the patient,
    including referring doctor details.
    """
    patient_name: str = Field(..., description="Full name of the patient", examples=["Mrs Test Patient"])
    patient_id: str = Field(..., description="Patient ID or registration number", examples=["ABB17985"])
    age_sex: str = Field(..., description="Age and sex of the patient", examples=["63Y / FEMALE"])
    sample_date: str = Field(..., description="Date and time when the sample was collected", examples=["08-11-2025 03:17 PM"])
    referring_doctor_full_name_titles: str = Field(
        ...,
        description="Full name and qualifications of the referring doctor",
        examples=["DR. John Doe MBBS, MD GENERAL MEDICINE, DNB CARDIOLOGY"]
    )


class LabReport(BaseModel):
    """Top-level schema for a complete laboratory report.
    
    Represents the full structure of a lab report including hospital information,
    patient details, and all test results.
    """
    hospital_info: HospitalInfo = Field(..., description="Hospital information")
    patient_info: PatientInfo = Field(..., description="Patient information")
    results: List[TestResult] = Field(..., description="List of test results")


def parse_sample_date(date_str: str) -> datetime:
    """
    Parse sample date string from lab report format to datetime.
    
    Expected format: "DD-MM-YYYY HH:MM AM/PM"
    Example: "08-11-2025 03:17 PM"
    
    Args:
        date_str: Date string in format "DD-MM-YYYY HH:MM AM/PM"
    
    Returns:
        datetime: Parsed datetime object
    
    Raises:
        ValueError: If date string cannot be parsed
    """
    try:
        # Parse format: "DD-MM-YYYY HH:MM AM/PM"
        return datetime.strptime(date_str, "%d-%m-%Y %I:%M %p")
    except ValueError as e:
        logger.error(f"Failed to parse sample date '{date_str}': {str(e)}")
        raise ValueError(f"Invalid date format: {date_str}. Expected format: DD-MM-YYYY HH:MM AM/PM") from e



@celery_app.task(bind=True, max_retries=3)
def process_uploaded_file(self, filename, file_path, file_size, content_type, upload_timestamp):
    """
    Process an uploaded file asynchronously.
    
    This task is queued after a file is successfully saved to disk.
    It can be used for post-processing operations such as:
    - Image processing (resizing, thumbnail generation, etc.)
    - Metadata extraction
    - Database logging
    - External service notifications
    
    Args:
        filename: Unique filename of the uploaded file
        file_path: Full path to the stored file
        file_size: Size of the file in bytes
        content_type: MIME type of the file
        upload_timestamp: ISO format timestamp of upload
    
    Returns:
        dict: Processing result with status and metadata
    
    Raises:
        Retry: If processing fails, the task will be retried up to 3 times
               with exponential backoff
    """
    try:
        logger.info(
            f"Processing uploaded file: {filename} "
            f"(size: {file_size} bytes, type: {content_type})"
        )
        
        # Verify file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.error(f"File not found at path: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Verify file size matches
        actual_size = file_path_obj.stat().st_size
        if actual_size != file_size:
            logger.warning(
                f"File size mismatch for {filename}: "
                f"expected {file_size}, got {actual_size}"
            )
        
        # Extract lab report data using Gemini AI
        try:
            gemini_service = GeminiService()
            lab_report = gemini_service.extract_lab_report(file_path)
            logger.info(f"Successfully extracted lab report data from file: {filename}")
        except Exception as e:
            logger.error(
                f"Failed to extract lab report data from file {filename}: {str(e)}",
                exc_info=True
            )
            # Re-raise to trigger retry mechanism
            raise
        
        # Store lab report records in database atomically
        records_saved = 0
        try:
            # Parse the lab report structure
            lab_report_obj = LabReport(**lab_report)
            
            # Parse sample date to datetime
            sample_timestamp = parse_sample_date(lab_report_obj.patient_info.sample_date)
            
            # Extract test results as list of dictionaries
            test_results = [
                {
                    "test_name": result.test_name,
                    "results": result.results,
                    "unit": result.unit
                }
                for result in lab_report_obj.results
            ]
            
            # Get database instance and save all records atomically
            db = get_database()
            record_ids = db.save_lab_report_records(
                patient_name=lab_report_obj.patient_info.patient_name,
                timestamp=sample_timestamp,
                lab_name=lab_report_obj.hospital_info.hospital_name,
                test_results=test_results
            )
            
            records_saved = len(record_ids)
            logger.info(
                f"Successfully stored {records_saved} health records "
                f"from lab report for file: {filename}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to store lab report records for file {filename}: {str(e)}",
                exc_info=True
            )
            # Re-raise to trigger retry mechanism
            raise
        
        # Log successful processing
        processed_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Successfully processed file: {filename} at {processed_at}")
        
        return {
            "status": "success",
            "filename": filename,
            "file_path": str(file_path),
            "file_size": file_size,
            "content_type": content_type,
            "upload_timestamp": upload_timestamp,
            "processed_at": processed_at,
            "lab_report": lab_report,
            "records_saved": records_saved
        }
        
    except FileNotFoundError as exc:
        logger.error(f"File not found error processing {filename}: {str(exc)}")
        # Don't retry if file doesn't exist
        raise
    except Exception as exc:
        logger.error(
            f"Error processing file {filename}: {str(exc)}",
            exc_info=True
        )
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

