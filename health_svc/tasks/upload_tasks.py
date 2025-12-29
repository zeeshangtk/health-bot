"""
Celery tasks for file upload processing.

Note: Celery tasks run outside the FastAPI request context, so they cannot
use FastAPI's Depends() mechanism. Instead, they create service instances
directly using the DI helper functions from core.dependencies.

Observability:
    - Task success/failure metrics are recorded via MetricsCollector
    - All logs include structured JSON fields for Grafana/Loki
    - Task IDs are logged for traceability
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from pydantic import ValidationError
from celery import shared_task

# Import services and DI helpers
from services.health_service import HealthService
from services.gemini_service import GeminiService
from services.paperless_ngx_service import PaperlessNgxService
from core.dependencies import get_patient_repository, get_health_record_repository
from core.exceptions import PatientNotFoundError

# Import schemas from single source of truth
from schemas.medical_info import TestResult, HospitalInfo, PatientInfo, LabReport

logger = logging.getLogger(__name__)


def _record_task_metrics(success: bool) -> None:
    """
    Record task completion metrics for Grafana dashboards.
    
    This function is called at the end of task execution to track
    success/failure rates. Safe to call even if metrics collector
    is not initialized (e.g., during testing).
    """
    try:
        from core.middleware import get_metrics_collector
        collector = get_metrics_collector()
        collector.record_task_result(success=success)
    except Exception as e:
        # Don't fail the task if metrics recording fails
        logger.warning(f"Failed to record task metrics: {e}")

# Constants
DEFAULT_RETRY_BASE_DELAY = 2  # seconds
MAX_RETRIES = 3
# Non-retryable errors - these indicate bad data or missing resources
# that won't be fixed by retrying
NON_RETRYABLE_ERRORS = (FileNotFoundError, ValueError, ValidationError, PatientNotFoundError)


def parse_sample_date(date_str: str) -> datetime:
    """
    Parse sample date string from lab report format to datetime.
    
    Expected format: "DD-MM-YYYY HH:MM AM/PM"
    Example: "08-11-2025 03:17 PM"
    
    Args:
        date_str: Date string in format "DD-MM-YYYY HH:MM AM/PM".
    
    Returns:
        datetime: Parsed datetime object.
    
    Raises:
        ValueError: If date string cannot be parsed.
    """
    formats = [
        "%d-%m-%Y %I:%M %p",  # 08-11-2025 03:17 PM
        "%d/%m/%Y %I:%M %p",  # 28/09/2025 03:17 PM
        "%d-%m-%Y %H:%M %p",  # 28-09-2025 00:00 AM (Gemini sometimes returns this)
        "%d/%m/%Y %H:%M %p",  # 28/09/2025 00:00 AM
        "%d-%m-%Y %H:%M",     # 08-11-2025 15:17
        "%d/%m/%Y %H:%M",     # 28/09/2025 15:17
        "%d-%m-%Y",           # 08-11-2025
        "%d/%m/%Y",           # 28/09/2025
        "%Y-%m-%d %H:%M:%S",  # 2025-11-08 15:17:00
        "%Y-%m-%d"            # 2025-11-08
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    # If all formats fail
    error_msg = f"Failed to parse sample date '{date_str}' with any of the expected formats."
    logger.error(error_msg)
    raise ValueError(f"{error_msg} Expected format like: DD-MM-YYYY HH:MM AM/PM")


def _calculate_retry_delay(retry_count: int, base_delay: int = DEFAULT_RETRY_BASE_DELAY) -> int:
    """
    Calculate exponential backoff delay for retries.
    
    Args:
        retry_count: Current retry attempt number (0-indexed).
        base_delay: Base delay in seconds (default: 2).
    
    Returns:
        int: Delay in seconds before next retry.
    """
    return base_delay ** retry_count


def validate_uploaded_file(file_path: Path, expected_size: int, filename: str) -> None:
    """
    Validate uploaded file exists and size matches.
    
    Args:
        file_path: Path to the file to validate.
        expected_size: Expected file size in bytes.
        filename: Filename for logging purposes.
    
    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path.exists():
        logger.error(f"File not found at path: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    actual_size = file_path.stat().st_size
    if actual_size != expected_size:
        logger.warning(
            f"File size mismatch for {filename}: "
            f"expected {expected_size}, got {actual_size}"
        )


def extract_lab_report_data(
    file_path: Path,
    gemini_service: Optional[GeminiService] = None
) -> Dict[str, Any]:
    """
    Extract lab report data using Gemini AI.
    
    Args:
        file_path: Path to the image file containing the lab report.
        gemini_service: Optional GeminiService instance (for testing).
    
    Returns:
        dict: Lab report data matching LabReport structure.
    
    Raises:
        FileNotFoundError: If file doesn't exist.
        Exception: For API or processing errors.
    """
    service = gemini_service or GeminiService()
    return service.extract_lab_report(str(file_path))


def convert_test_results_to_dicts(test_results: List[TestResult]) -> List[Dict[str, str]]:
    """
    Convert TestResult objects to database-ready dictionaries.
    
    Args:
        test_results: List of TestResult Pydantic models.
    
    Returns:
        List of dictionaries with keys: test_name, results, unit.
    """
    return [
        {
            "test_name": result.test_name,
            "results": result.results,
            "unit": result.unit
        }
        for result in test_results
    ]


def transform_lab_report_to_records(
    lab_report: Dict[str, Any]
) -> Tuple[LabReport, datetime, List[Dict[str, str]]]:
    """
    Transform lab report dictionary to database-ready format.
    
    Args:
        lab_report: Raw lab report dictionary from Gemini AI.
    
    Returns:
        Tuple of (LabReport object, parsed sample timestamp, test results dicts).
    
    Raises:
        ValidationError: If lab report structure is invalid.
        ValueError: If sample date cannot be parsed.
    """
    # Parse the lab report structure
    lab_report_obj = LabReport(**lab_report)
    
    # Parse sample date to datetime
    sample_timestamp = parse_sample_date(lab_report_obj.patient_info.sample_date)
    
    # Extract test results as list of dictionaries
    test_results = convert_test_results_to_dicts(lab_report_obj.results)
    
    return lab_report_obj, sample_timestamp, test_results


def save_lab_report_to_database(
    lab_report_obj: LabReport,
    sample_timestamp: datetime,
    health_service: Optional[HealthService] = None,
    patient_name: Optional[str] = None
) -> int:
    """
    Save lab report records to database atomically.
    
    Args:
        lab_report_obj: Parsed LabReport object.
        sample_timestamp: Parsed sample collection timestamp.
        health_service: Optional HealthService instance (for testing).
        patient_name: Optional patient name to override extracted name.
    
    Returns:
        int: Number of records saved.
    
    Raises:
        PatientNotFoundError: If patient is not found in database.
        DatabaseError: For database errors.
    """
    # Extract test results as list of dictionaries
    test_results = convert_test_results_to_dicts(lab_report_obj.results)
    
    # Use provided patient name or fallback to extracted one
    final_patient_name = patient_name or lab_report_obj.patient_info.patient_name
    
    # Get service instance via DI pattern
    # Note: In Celery tasks, we can't use FastAPI's Depends(), so we
    # manually construct the service with injected dependencies
    if health_service is None:
        patient_repo = get_patient_repository()
        record_repo = get_health_record_repository()
        health_service = HealthService(
            patient_repository=patient_repo,
            health_record_repository=record_repo
        )
    
    # Save all records atomically
    # This now raises PatientNotFoundError instead of ValueError
    records_saved = health_service.save_lab_report_records(
        patient_name=final_patient_name,
        timestamp=sample_timestamp,
        lab_name=lab_report_obj.hospital_info.hospital_name,
        test_results=test_results
    )
    
    return records_saved


def create_processing_result(
    filename: str,
    file_path: Path,
    file_size: int,
    content_type: str,
    upload_timestamp: str,
    lab_report: Dict[str, Any],
    records_saved: int
) -> Dict[str, Any]:
    """
    Create standardized processing result dictionary.
    
    Args:
        filename: Unique filename of the uploaded file.
        file_path: Full path to the stored file.
        file_size: Size of the file in bytes.
        content_type: MIME type of the file.
        upload_timestamp: ISO format timestamp of upload.
        lab_report: Extracted lab report data.
        records_saved: Number of records saved to database.
    
    Returns:
        dict: Processing result with status and metadata.
    """
    return {
        "status": "success",
        "filename": filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "content_type": content_type,
        "upload_timestamp": upload_timestamp,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "lab_report": lab_report,
        "records_saved": records_saved
    }



@shared_task(bind=True, max_retries=MAX_RETRIES)
def process_uploaded_file(
    self,
    filename: str,
    file_path: str,
    file_size: int,
    content_type: str,
    upload_timestamp: str,
    patient_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process an uploaded file asynchronously.
    
    This task orchestrates the complete workflow:
    1. Validate file exists and size matches
    2. Extract lab report data using Gemini AI
    3. Transform and save lab report to database
    4. Return processing result
    
    Args:
        self: Celery task instance (bound task).
        filename: Unique filename of the uploaded file.
        file_path: Full path to the stored file.
        file_size: Size of the file in bytes.
        content_type: MIME type of the file.
        upload_timestamp: ISO format timestamp of upload.
        patient_name: Optional patient name to associate with the record.
    
    Returns:
        dict: Processing result with status and metadata.
    
    Raises:
        FileNotFoundError: If file doesn't exist (non-retryable).
        ValueError: If data validation fails (non-retryable).
        ValidationError: If lab report structure is invalid (non-retryable).
        Retry: If processing fails with retryable error, task will be retried
               up to MAX_RETRIES times with exponential backoff.
    """
    try:
        logger.info(
            f"Processing uploaded file: {filename} "
            f"(size: {file_size} bytes, type: {content_type})"
        )
        
        file_path_obj = Path(file_path)
        
        # Step 1: Validate file
        validate_uploaded_file(file_path_obj, file_size, filename)
        
        # Step 2: Extract lab report data
        lab_report = extract_lab_report_data(file_path_obj)
        logger.info(f"Successfully extracted lab report data from file: {filename}")
        
        # Step 2.5: Upload to Paperless NGX
        try:
            paperless_service = PaperlessNgxService()
            paperless_result = paperless_service.upload_medical_document_from_dict(
                document_path=str(file_path_obj),
                medical_info=lab_report
            )
            logger.info(
                f"Successfully uploaded document to Paperless NGX: {filename}. "
                f"Result: {paperless_result}"
            )
        except Exception as paperless_exc:
            # Log error but don't fail the entire task if Paperless NGX upload fails
            logger.warning(
                f"Failed to upload document to Paperless NGX for {filename}: {paperless_exc}",
                exc_info=True
            )
        
        # Step 3: Transform and save to database
        lab_report_obj, sample_timestamp, _ = transform_lab_report_to_records(lab_report)
        records_saved = save_lab_report_to_database(
            lab_report_obj, 
            sample_timestamp, 
            patient_name=patient_name
        )
        logger.info(
            f"Successfully stored {records_saved} health records "
            f"from lab report for file: {filename}"
        )
        
        # Step 4: Return result
        result = create_processing_result(
            filename=filename,
            file_path=file_path_obj,
            file_size=file_size,
            content_type=content_type,
            upload_timestamp=upload_timestamp,
            lab_report=lab_report,
            records_saved=records_saved
        )
        
        logger.info(
            f"Successfully processed file: {filename}",
            extra={
                "task_id": self.request.id,
                "uploaded_file": filename,  # Note: can't use "filename" - reserved by LogRecord
                "records_saved": records_saved,
                "processed_at": result['processed_at']
            }
        )
        
        # Record success metric for Grafana dashboard
        _record_task_metrics(success=True)
        
        return result
        
    except NON_RETRYABLE_ERRORS as exc:
        logger.error(
            f"Non-retryable error processing {filename}: {exc}",
            extra={
                "task_id": self.request.id,
                "uploaded_file": filename,  # Note: can't use "filename" - reserved by LogRecord
                "error_type": type(exc).__name__
            }
        )
        # Record failure metric for Grafana dashboard
        _record_task_metrics(success=False)
        # Don't retry validation/data errors
        raise
        
    except Exception as exc:
        # Only record failure if we've exhausted retries
        if self.request.retries >= MAX_RETRIES:
            logger.error(
                f"Max retries exhausted for {filename}: {exc}",
                extra={
                    "task_id": self.request.id,
                    "uploaded_file": filename,  # Note: can't use "filename" - reserved by LogRecord
                    "retries": self.request.retries
                }
            )
            _record_task_metrics(success=False)
        else:
            logger.warning(
                f"Retrying task for {filename}: {exc}",
                extra={
                    "task_id": self.request.id,
                    "uploaded_file": filename,  # Note: can't use "filename" - reserved by LogRecord
                    "retry_count": self.request.retries + 1
                }
            )
        
        # Retry with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=_calculate_retry_delay(self.request.retries)
        )
