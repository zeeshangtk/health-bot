"""
Validation utilities for file uploads.

This module contains validation logic for file upload operations.
"""
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from typing import Tuple

logger = logging.getLogger(__name__)

# Allowed image MIME types and extensions
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/bmp": [".bmp"]
}
ALLOWED_EXTENSIONS = {ext for exts in ALLOWED_IMAGE_TYPES.values() for ext in exts}


def validate_file_present(file: UploadFile) -> None:
    """
    Validate that a file is provided in the upload request.
    
    Args:
        file: The uploaded file object.
        
    Raises:
        HTTPException: 400 Bad Request if no file is provided.
    """
    if not file:
        logger.error("No file provided in upload request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )


def validate_content_type(file: UploadFile) -> str:
    """
    Validate that the file has a valid content type.
    
    Args:
        file: The uploaded file object.
        
    Returns:
        str: The validated content type.
        
    Raises:
        HTTPException: 400 Bad Request if content type is missing or invalid.
    """
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
    
    return file.content_type


def validate_file_extension(file: UploadFile, content_type: str) -> str:
    """
    Validate that the file has a valid extension that matches the content type.
    
    Args:
        file: The uploaded file object.
        content_type: The validated content type.
        
    Returns:
        str: The validated file extension (with leading dot).
        
    Raises:
        HTTPException: 400 Bad Request if extension is missing, invalid, or doesn't match content type.
    """
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""
    
    if not file_extension or file_extension not in ALLOWED_EXTENSIONS:
        logger.error(f"Invalid file extension: {file_extension}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    # Verify extension matches content type
    expected_extensions = ALLOWED_IMAGE_TYPES.get(content_type, [])
    if file_extension not in expected_extensions:
        logger.error(f"File extension {file_extension} does not match content type {content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File extension does not match content type"
        )
    
    return file_extension


def validate_file_size(file_size: int, max_size: int) -> None:
    """
    Validate that the file size is within allowed limits.
    
    Args:
        file_size: Size of the file in bytes.
        max_size: Maximum allowed file size in bytes.
        
    Raises:
        HTTPException: 400 Bad Request if file is empty, 413 Payload Too Large if exceeds max size.
    """
    if file_size == 0:
        logger.error("Empty file uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    if file_size > max_size:
        logger.error(f"File size {file_size} exceeds maximum {max_size}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {max_size / (1024 * 1024):.1f}MB"
        )


def validate_upload_file(file: UploadFile, max_size: int) -> Tuple[str, str]:
    """
    Perform all validation checks on an uploaded file.
    
    This is a convenience function that runs all validation checks in sequence:
    1. File presence
    2. Content type
    3. File extension
    4. File size (requires file content to be read)
    
    Args:
        file: The uploaded file object.
        max_size: Maximum allowed file size in bytes.
        
    Returns:
        Tuple[str, str]: A tuple of (content_type, file_extension).
        
    Raises:
        HTTPException: Various status codes depending on validation failure.
    """
    validate_file_present(file)
    content_type = validate_content_type(file)
    file_extension = validate_file_extension(file, content_type)
    
    # Note: File size validation requires reading the file content,
    # so it's handled separately in the service layer after reading
    
    return content_type, file_extension

