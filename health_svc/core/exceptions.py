"""
Shared exception classes and error handling utilities for Health Service API.

This module provides:
- Custom exception hierarchy for domain-specific errors
- Consistent error response formatting
- Exception handlers for FastAPI integration

Usage:
    from core.exceptions import PatientNotFoundError, DuplicatePatientError
    
    # In service layer - raise domain exceptions
    raise PatientNotFoundError(patient_name="John Doe")
    
    # In FastAPI - register handlers via setup_exception_handlers(app)
"""
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# BASE EXCEPTION CLASSES
# =============================================================================

class HealthServiceError(Exception):
    """
    Base exception for all Health Service domain errors.
    
    All custom exceptions should inherit from this class.
    Provides consistent error structure with status code and detail message.
    """
    
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred"
    
    def __init__(
        self,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs: Any
    ):
        """
        Initialize the exception.
        
        Args:
            detail: Human-readable error message. Uses class default if not provided.
            status_code: HTTP status code. Uses class default if not provided.
            **kwargs: Additional context to include in error response.
        """
        self.detail = detail or self.__class__.detail
        self.status_code = status_code or self.__class__.status_code
        self.context = kwargs
        super().__init__(self.detail)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {"detail": self.detail}
        if self.context:
            result["context"] = self.context
        return result


# =============================================================================
# PATIENT EXCEPTIONS
# =============================================================================

class PatientNotFoundError(HealthServiceError):
    """Raised when a patient is not found in the database."""
    
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Patient not found"
    
    def __init__(self, patient_name: Optional[str] = None, **kwargs: Any):
        detail = f"Patient '{patient_name}' not found" if patient_name else self.detail
        super().__init__(detail=detail, patient_name=patient_name, **kwargs)


class DuplicatePatientError(HealthServiceError):
    """Raised when attempting to create a patient that already exists."""
    
    status_code = status.HTTP_409_CONFLICT
    detail = "Patient already exists"
    
    def __init__(self, patient_name: Optional[str] = None, **kwargs: Any):
        detail = f"Patient '{patient_name}' already exists" if patient_name else self.detail
        super().__init__(detail=detail, patient_name=patient_name, **kwargs)


# =============================================================================
# RECORD EXCEPTIONS
# =============================================================================

class RecordNotFoundError(HealthServiceError):
    """Raised when a health record is not found."""
    
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Health record not found"


class InvalidRecordDataError(HealthServiceError):
    """Raised when record data fails validation."""
    
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Invalid record data"


# =============================================================================
# DATABASE EXCEPTIONS
# =============================================================================

class DatabaseError(HealthServiceError):
    """Raised when a database operation fails."""
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Database operation failed"
    
    def __init__(self, operation: Optional[str] = None, **kwargs: Any):
        detail = f"Database error during {operation}" if operation else self.detail
        super().__init__(detail=detail, operation=operation, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    detail = "Failed to connect to database"


# =============================================================================
# UPLOAD EXCEPTIONS
# =============================================================================

class UploadError(HealthServiceError):
    """Base exception for upload-related errors."""
    
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Upload failed"


class InvalidFileTypeError(UploadError):
    """Raised when uploaded file has invalid type."""
    
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    detail = "Unsupported file type"


class FileTooLargeError(UploadError):
    """Raised when uploaded file exceeds size limit."""
    
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    detail = "File size exceeds maximum allowed"


# =============================================================================
# EXTERNAL SERVICE EXCEPTIONS
# =============================================================================

class ExternalServiceError(HealthServiceError):
    """Raised when an external service call fails."""
    
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "External service error"


class GeminiServiceError(ExternalServiceError):
    """Raised when Gemini AI service fails."""
    
    detail = "Gemini AI service error"


class PaperlessServiceError(ExternalServiceError):
    """Raised when Paperless NGX service fails."""
    
    detail = "Paperless NGX service error"


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

async def health_service_exception_handler(
    request: Request,
    exc: HealthServiceError
) -> JSONResponse:
    """
    Handle HealthServiceError exceptions and return consistent JSON responses.
    
    This handler logs the error and returns a standardized JSON error response.
    """
    logger.warning(
        f"HealthServiceError: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "context": exc.context
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions with a generic error response.
    
    Logs the full exception for debugging but returns a safe error message.
    """
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"}
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register exception handlers with the FastAPI application.
    
    Call this function during app initialization to enable consistent
    error handling across all endpoints.
    
    Args:
        app: The FastAPI application instance.
    
    Example:
        app = FastAPI()
        setup_exception_handlers(app)
    """
    app.add_exception_handler(HealthServiceError, health_service_exception_handler)
    # Uncomment to catch all unhandled exceptions:
    # app.add_exception_handler(Exception, generic_exception_handler)


