"""
Pydantic schemas for file upload operations.
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    """Schema for image upload response.
    
    Returns success status, stored filename, and a success message after image upload.
    Optionally includes task_id for tracking background processing tasks.
    """
    status: str = Field(..., description="Upload status", example="success")
    filename: str = Field(..., description="Unique filename of the stored image", example="a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg")
    message: str = Field(..., description="Success message", example="Image uploaded successfully")
    task_id: Optional[str] = Field(None, description="Celery task ID for background processing (optional)", example="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
                "message": "Image uploaded successfully",
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }


class UploadStatusResponse(BaseModel):
    """Schema for polling the status of a background upload-processing task.

    `status` mirrors the Celery task state (PENDING, PROGRESS, SUCCESS, FAILURE).
    `stage`/`detail` are only populated while the task reports PROGRESS.
    `result` is populated once the task finishes successfully; `error` is
    populated if it fails.
    """
    status: str = Field(..., description="Celery task state", example="PROGRESS")
    stage: Optional[str] = Field(None, description="Current processing stage", example="extracting")
    detail: Optional[str] = Field(None, description="Human-readable description of the current stage")
    result: Optional[Dict[str, Any]] = Field(None, description="Processing result, present once status is SUCCESS")
    error: Optional[str] = Field(None, description="Error message, present once status is FAILURE")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "PROGRESS",
                "stage": "extracting",
                "detail": "Reading lab report with Gemini AI",
                "result": None,
                "error": None
            }
        }

