"""
Pydantic schemas for file upload operations.
"""
from typing import Optional

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

