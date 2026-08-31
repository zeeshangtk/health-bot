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
from core.date_utils import parse_sample_date

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


def _report_progress(task, stage: str, detail: str) -> None:
    """
    Report a PROGRESS state for live status polling (GET /upload/status/{task_id}).

    Guarded on task.request.id: it's only unset when a task is invoked
    directly (e.g. via .run() in unit tests) rather than through Celery's
    .delay()/.apply_async(), in which case there's no task_id to report
    progress against anyway.
    """
    if not getattr(task.request, "id", None):
        return
    try:
        task.update_state(state="PROGRESS", meta={"stage": stage, "detail": detail})
    except Exception as e:
        logger.warning(f"Failed to report progress ({stage}): {e}")

# Constants
RETRY_DELAY_SECONDS = 5
MAX_RETRIES = 3
# Non-retryable errors - these indicate bad data or missing resources
# that won't be fixed by retrying
NON_RETRYABLE_ERRORS = (FileNotFoundError, ValueError, ValidationError, PatientNotFoundError)


def _format_validation_error(exc: ValidationError) -> str:
    """
    Render a pydantic ValidationError as a short human-readable string.

    pydantic_core.ValidationError can't be reconstructed by Celery's JSON
    result backend (it round-trips exceptions via `cls(*exc.args)`, but
    `.args` is always empty on this exception and its constructor doesn't
    accept positional args) - it comes back as an opaque
    "<class '...ValidationError'>([])" string. Formatting the real detail
    into a plain string here, then raising a builtin Exception with it,
    keeps the useful message intact through that round-trip.
    """
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


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

    Rows with no result value are skipped: the health_records table's
    `value` column is NOT NULL, and a row with nothing extracted isn't
    meaningful to persist.

    Args:
        test_results: List of TestResult Pydantic models.

    Returns:
        List of dictionaries with keys: test_name, results, unit.
    """
    dicts = []
    for result in test_results:
        if result.results is None:
            logger.warning(f"Skipping test result with no value: {result.test_name}")
            continue
        dicts.append({
            "test_name": result.test_name,
            "results": result.results,
            "unit": result.unit
        })
    return dicts


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
    records_saved: int,
    paperless_status: str = "skipped"
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
        paperless_status: One of "ok", "failed", "skipped" - outcome of the
            best-effort Paperless NGX archival step.

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
        "records_saved": records_saved,
        "paperless_status": paperless_status
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
               up to MAX_RETRIES times, waiting RETRY_DELAY_SECONDS between attempts.
    """
    try:
        logger.info(
            f"Processing uploaded file: {filename} "
            f"(size: {file_size} bytes, type: {content_type})"
        )
        
        file_path_obj = Path(file_path)

        # Step 1: Validate file
        _report_progress(self, stage="validating", detail="Checking uploaded file")
        validate_uploaded_file(file_path_obj, file_size, filename)

        # Step 2: Extract lab report data
        _report_progress(self, stage="extracting", detail="Reading lab report with Gemini AI")
        lab_report = extract_lab_report_data(file_path_obj)
        logger.info(f"Successfully extracted lab report data from file: {filename}")

        # Step 2.1: Override patient name if provided (takes precedence over Gemini extraction)
        if patient_name and lab_report.get("patient_info"):
            extracted_name = lab_report["patient_info"].get("patient_name", "Unknown")
            lab_report["patient_info"]["patient_name"] = patient_name
            logger.info(
                f"Overriding extracted patient name '{extracted_name}' with provided name '{patient_name}'"
            )

        # Step 2.5: Upload to Paperless NGX
        _report_progress(self, stage="archiving", detail="Archiving document to Paperless NGX")
        paperless_status = "ok"
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
            # Log error but don't fail the entire task if Paperless NGX upload fails.
            # The failure is still surfaced to the user via paperless_status in the result.
            paperless_status = "failed"
            logger.warning(
                f"Failed to upload document to Paperless NGX for {filename}: {paperless_exc}",
                exc_info=True
            )

        # Step 3: Transform and save to database
        _report_progress(self, stage="saving", detail="Saving extracted values")
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
            records_saved=records_saved,
            paperless_status=paperless_status
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
        
    except ValidationError as exc:
        message = f"Lab report data failed validation ({_format_validation_error(exc)})"
        logger.error(
            f"Non-retryable error processing {filename}: {message}",
            extra={
                "task_id": self.request.id,
                "uploaded_file": filename,  # Note: can't use "filename" - reserved by LogRecord
                "error_type": type(exc).__name__
            }
        )
        # Record failure metric for Grafana dashboard
        _record_task_metrics(success=False)
        # Re-raise as a plain Exception: pydantic_core.ValidationError can't be
        # reconstructed by Celery's result backend, so raising it directly leaves
        # the caller with an opaque "<class '...'>([])" string instead of this message.
        raise Exception(message) from exc

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
        
        # Retry after a fixed delay, up to MAX_RETRIES times
        raise self.retry(
            exc=exc,
            countdown=RETRY_DELAY_SECONDS
        )
