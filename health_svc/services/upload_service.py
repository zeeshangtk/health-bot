"""
Service for handling file upload operations.
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from typing import Tuple, Optional

from config import UPLOAD_DIR, UPLOAD_MAX_SIZE
from tasks.upload_tasks import process_uploaded_file
from api.utils.upload_validator import validate_upload_file, validate_file_size

logger = logging.getLogger(__name__)


class UploadService:
    """Service for handling file uploads."""
    
    def __init__(self, upload_dir: str = UPLOAD_DIR, max_size: int = UPLOAD_MAX_SIZE):
        """
        Initialize the upload service.
        
        Args:
            upload_dir: Directory where uploaded files will be stored
            max_size: Maximum allowed file size in bytes
        """
        self.upload_dir = Path(upload_dir)
        self.max_size = max_size
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_uploaded_file(
        self,
        file: UploadFile,
        queue_background_task: bool = True
    ) -> Tuple[str, str, Optional[str]]:
        """
        Save an uploaded file to disk and optionally queue background processing.
        
        This method:
        1. Validates the uploaded file (type, extension, size)
        2. Generates a unique filename
        3. Saves the file to disk
        4. Optionally queues a Celery task for background processing
        
        Args:
            file: The uploaded file object
            queue_background_task: Whether to queue a Celery task for background processing
            
        Returns:
            Tuple[str, str, Optional[str]]: A tuple of (unique_filename, file_path, task_id)
                - unique_filename: The generated unique filename
                - file_path: Full path to the saved file
                - task_id: Celery task ID if queued, None otherwise
                
        Raises:
            HTTPException: Various status codes depending on validation or I/O failures
        """
        # Validate file (content type and extension)
        content_type, file_extension = validate_upload_file(file, self.max_size)
        
        try:
            # Read file content to check size and validate
            file_content = await file.read()
            file_size = len(file_content)
            
            # Validate file size
            validate_file_size(file_size, self.max_size)
            
            # Generate unique filename
            unique_id = str(uuid.uuid4())
            unique_filename = f"{unique_id}{file_extension}"
            upload_path = self.upload_dir / unique_filename
            
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
            
            # Queue Celery task for background processing
            task_id = None
            if queue_background_task:
                try:
                    upload_timestamp = datetime.now(timezone.utc).isoformat()
                    task = process_uploaded_file.delay(
                        filename=unique_filename,
                        file_path=str(upload_path),
                        file_size=file_size,
                        content_type=content_type,
                        upload_timestamp=upload_timestamp
                    )
                    task_id = task.id
                    logger.info(f"Queued background processing task {task_id} for file: {unique_filename}")
                except Exception as e:
                    # Log error but don't fail the upload if task queuing fails
                    logger.error(
                        f"Failed to queue background processing task for {unique_filename}: {str(e)}",
                        exc_info=True
                    )
                    # Continue with response even if task queuing failed
            
            return unique_filename, str(upload_path), task_id
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during file upload: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the upload"
            )

