"""
Celery tasks for file upload processing.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from celery_app import celery_app

logger = logging.getLogger(__name__)


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
        
        # Add your processing logic here
        # Examples:
        # - Image processing (resize, thumbnail generation)
        # - Metadata extraction (EXIF data, dimensions, etc.)
        # - Database logging of upload events
        # - External service notifications
        # - Virus scanning
        # - Content analysis
        
        # For now, we'll just log the successful processing
        processed_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Successfully processed file: {filename} at {processed_at}")
        
        return {
            "status": "success",
            "filename": filename,
            "file_path": str(file_path),
            "file_size": file_size,
            "content_type": content_type,
            "upload_timestamp": upload_timestamp,
            "processed_at": processed_at
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

