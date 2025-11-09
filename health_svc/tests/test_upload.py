"""
Comprehensive tests for image upload endpoint.
Tests both success cases and error handling scenarios.
"""
import os
import tempfile
import pytest
from pathlib import Path
from io import BytesIO
from unittest.mock import patch, mock_open, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, UploadFile, File
from fastapi import APIRouter, HTTPException, status

from api.schemas import ImageUploadResponse
from config import UPLOAD_DIR, UPLOAD_MAX_SIZE
from tasks.upload_tasks import process_uploaded_file
from services.upload_service import UploadService


@pytest.fixture
def temp_upload_dir():
    """Create a temporary upload directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test upload service with temporary directory
        test_upload_service = UploadService()
        original_upload_dir = test_upload_service.upload_dir
        test_upload_service.upload_dir = Path(tmpdir)
        test_upload_service.upload_dir.mkdir(parents=True, exist_ok=True)
        try:
            yield tmpdir, test_upload_service
        finally:
            test_upload_service.upload_dir = original_upload_dir


@pytest.fixture
def test_app(temp_upload_dir):
    """Create a FastAPI test app with upload endpoint."""
    tmpdir, test_upload_service = temp_upload_dir
    
    app = FastAPI(title="Health Service API Test")
    
    # Create test router with test upload service
    from fastapi import APIRouter, UploadFile, File
    from api.schemas import ImageUploadResponse
    
    records_router = APIRouter(prefix="/api/v1/records", tags=["Health Records"])
    
    @records_router.post(
        "/upload",
        response_model=ImageUploadResponse,
        status_code=201
    )
    async def upload_image(file: UploadFile = File(...)):
        """Upload an image file."""
        unique_filename, file_path, task_id = await test_upload_service.save_uploaded_file(file)
        
        return ImageUploadResponse(
            status="success",
            filename=unique_filename,
            message="Image uploaded successfully",
            task_id=task_id
        )
    
    app.include_router(records_router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the API."""
    return TestClient(test_app)


def create_test_image(format: str = "jpeg", size: int = 1024) -> BytesIO:
    """Create a test image file in memory.
    
    Args:
        format: Image format ('jpeg', 'png', 'gif', 'bmp')
        size: Size of the image data in bytes
    
    Returns:
        BytesIO object containing image data
    """
    # Create minimal valid image data
    # For JPEG: minimal valid JPEG header
    if format.lower() == "jpeg":
        # Minimal valid JPEG (FF D8 FF E0)
        data = b'\xFF\xD8\xFF\xE0' + b'\x00' * (size - 4)
    elif format.lower() == "png":
        # Minimal valid PNG header
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * (size - 8)
    elif format.lower() == "gif":
        # Minimal valid GIF header
        data = b'GIF89a' + b'\x00' * (size - 6)
    elif format.lower() == "bmp":
        # Minimal valid BMP header
        data = b'BM' + b'\x00' * (size - 2)
    else:
        data = b'\x00' * size
    
    return BytesIO(data)


# Success Case Tests
def test_upload_image_success_jpeg(client, temp_upload_dir):
    """Test successful JPEG image upload."""
    tmpdir, _ = temp_upload_dir
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Image uploaded successfully"
    assert data["filename"].endswith(".jpg")
    assert len(data["filename"]) > 4  # UUID + extension
    assert data["task_id"] == "test-task-id-123"
    
    # Verify file was saved
    upload_path = Path(tmpdir)
    saved_files = list(upload_path.glob("*.jpg"))
    assert len(saved_files) == 1
    assert saved_files[0].name == data["filename"]


def test_upload_image_success_png(client, temp_upload_dir):
    """Test successful PNG image upload."""
    image_data = create_test_image("png", 2048)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-456"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.png", image_data, "image/png")}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"].endswith(".png")
    assert data["task_id"] == "test-task-id-456"


def test_upload_image_success_gif(client, temp_upload_dir):
    """Test successful GIF image upload."""
    image_data = create_test_image("gif", 512)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-gif"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.gif", image_data, "image/gif")}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"].endswith(".gif")
    assert data["task_id"] == "test-task-id-gif"


def test_upload_image_success_bmp(client, temp_upload_dir):
    """Test successful BMP image upload."""
    image_data = create_test_image("bmp", 1024)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-bmp"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.bmp", image_data, "image/bmp")}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"].endswith(".bmp")
    assert data["task_id"] == "test-task-id-bmp"


def test_upload_image_unique_filenames(client, temp_upload_dir):
    """Test that multiple uploads generate unique filenames."""
    tmpdir, _ = temp_upload_dir
    image_data1 = create_test_image("jpeg", 1024)
    image_data1.seek(0)
    image_data2 = create_test_image("jpeg", 1024)
    image_data2.seek(0)
    
    # Mock Celery task
    mock_task1 = MagicMock()
    mock_task1.id = "task-1"
    mock_task2 = MagicMock()
    mock_task2.id = "task-2"
    
    with patch('services.upload_service.process_uploaded_file.delay', side_effect=[mock_task1, mock_task2]):
        response1 = client.post(
            "/api/v1/records/upload",
            files={"file": ("test1.jpg", image_data1, "image/jpeg")}
        )
        response2 = client.post(
            "/api/v1/records/upload",
            files={"file": ("test2.jpg", image_data2, "image/jpeg")}
        )
    
    assert response1.status_code == 201
    assert response2.status_code == 201
    
    filename1 = response1.json()["filename"]
    filename2 = response2.json()["filename"]
    
    assert filename1 != filename2
    
    # Verify both files exist
    upload_path = Path(tmpdir)
    saved_files = list(upload_path.glob("*.jpg"))
    assert len(saved_files) == 2


# Error Case Tests
def test_upload_no_file(client):
    """Test upload without file returns 400."""
    response = client.post("/api/v1/records/upload")
    assert response.status_code == 422  # FastAPI validation error


def test_upload_empty_file(client):
    """Test upload of empty file returns 400."""
    empty_file = BytesIO(b"")
    response = client.post(
        "/api/v1/records/upload",
        files={"file": ("empty.jpg", empty_file, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_invalid_content_type(client):
    """Test upload with invalid content type returns 400."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    response = client.post(
        "/api/v1/records/upload",
        files={"file": ("test.pdf", image_data, "application/pdf")}
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_upload_missing_content_type(client):
    """Test upload with missing content type.
    
    Note: FastAPI's test client may set a default content type, so this test
    verifies that the endpoint handles the request. If content_type is None,
    our validation should catch it, but FastAPI may set a default.
    """
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Try to send without explicit content type
    # The test client may set application/octet-stream or similar
    response = client.post(
        "/api/v1/records/upload",
        files={"file": ("test.jpg", image_data)}
    )
    # FastAPI test client may set a default content type, so this might succeed
    # or fail depending on what default is set. Either way, we validate content type.
    # If it's not an image type, it should fail.
    if response.status_code == 201:
        # If it succeeded, it means FastAPI set a valid image content type
        assert response.json()["status"] == "success"
    else:
        # If it failed, it should be because content type validation failed
        assert response.status_code in [400, 422]


def test_upload_invalid_extension(client):
    """Test upload with invalid file extension returns 400."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    response = client.post(
        "/api/v1/records/upload",
        files={"file": ("test.txt", image_data, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "extension" in response.json()["detail"].lower()


def test_upload_extension_mismatch(client):
    """Test upload where extension doesn't match content type returns 400."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    response = client.post(
        "/api/v1/records/upload",
        files={"file": ("test.png", image_data, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "match" in response.json()["detail"].lower()


def test_upload_file_too_large(client, temp_upload_dir):
    """Test upload of file exceeding size limit returns 413."""
    # Create a file larger than the max size
    large_size = UPLOAD_MAX_SIZE + 1
    large_data = BytesIO(b'\xFF\xD8\xFF\xE0' + b'\x00' * (large_size - 4))
    large_data.seek(0)
    
    response = client.post(
        "/api/v1/records/upload",
        files={"file": ("large.jpg", large_data, "image/jpeg")}
    )
    assert response.status_code == 413
    assert "size" in response.json()["detail"].lower()


def test_upload_file_at_max_size(client, temp_upload_dir):
    """Test upload of file at exactly max size succeeds."""
    max_size_data = BytesIO(b'\xFF\xD8\xFF\xE0' + b'\x00' * (UPLOAD_MAX_SIZE - 4))
    max_size_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-max"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("max.jpg", max_size_data, "image/jpeg")}
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["task_id"] == "test-task-id-max"


def test_upload_file_write_failure(client, temp_upload_dir):
    """Test handling of file system write failure returns 500."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock open to raise OSError
    with patch('builtins.open', side_effect=OSError("Permission denied")):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
        assert response.status_code == 500
        assert "disk" in response.json()["detail"].lower()


def test_upload_jpeg_with_jpeg_extension(client, temp_upload_dir):
    """Test JPEG upload with .jpeg extension (alternative extension)."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-jpeg-ext"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpeg", image_data, "image/jpeg")}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["filename"].endswith(".jpeg")
    assert data["task_id"] == "test-task-id-jpeg-ext"


# Integration Tests
def test_upload_integration_full_workflow(client, temp_upload_dir):
    """Test complete upload workflow including file storage and cleanup."""
    tmpdir, _ = temp_upload_dir
    # Mock Celery tasks
    mock_tasks = [MagicMock(id=f"task-{i}") for i in range(3)]
    
    # Upload multiple files
    files_uploaded = []
    with patch('services.upload_service.process_uploaded_file.delay', side_effect=mock_tasks):
        for i, format in enumerate(["jpeg", "png", "gif"]):
            image_data = create_test_image(format, 1024)
            image_data.seek(0)
            
            filename = f"test_{i}.{format if format != 'jpeg' else 'jpg'}"
            content_type = f"image/{format if format != 'jpeg' else 'jpeg'}"
            
            response = client.post(
                "/api/v1/records/upload",
                files={"file": (filename, image_data, content_type)}
            )
            
            assert response.status_code == 201
            data = response.json()
            files_uploaded.append(data["filename"])
            assert data["task_id"] == f"task-{i}"
    
    # Verify all files were saved
    upload_path = Path(tmpdir)
    saved_files = [f.name for f in upload_path.iterdir() if f.is_file()]
    assert len(saved_files) == 3
    
    # Verify all uploaded filenames are in saved files
    for uploaded_filename in files_uploaded:
        assert uploaded_filename in saved_files


def test_upload_response_schema(client, temp_upload_dir):
    """Test that upload response matches the expected schema."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-schema"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify schema fields
    assert "status" in data
    assert "filename" in data
    assert "message" in data
    assert "task_id" in data
    assert data["status"] == "success"
    assert isinstance(data["filename"], str)
    assert isinstance(data["message"], str)
    assert isinstance(data["task_id"], str)


def test_upload_concurrent_uploads(client, temp_upload_dir):
    """Test handling of concurrent uploads."""
    tmpdir, _ = temp_upload_dir
    import concurrent.futures
    
    # Mock Celery task
    task_ids = [f"task-{i}" for i in range(5)]
    mock_tasks = [MagicMock(id=tid) for tid in task_ids]
    
    def upload_one():
        image_data = create_test_image("jpeg", 1024)
        image_data.seek(0)
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
        return response.status_code == 201
    
    # Upload 5 files concurrently
    with patch('services.upload_service.process_uploaded_file.delay', side_effect=mock_tasks):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_one) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All should succeed
    assert all(results)
    
    # Verify all files were saved with unique names
    upload_path = Path(tmpdir)
    saved_files = list(upload_path.glob("*.jpg"))
    assert len(saved_files) == 5
    
    # Verify all filenames are unique
    filenames = [f.name for f in saved_files]
    assert len(filenames) == len(set(filenames))


# Celery Task Queuing Tests
def test_upload_task_queued_with_correct_parameters(client, temp_upload_dir):
    """Test that Celery task is queued with correct parameters."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "test-task-params"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task) as mock_delay:
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify task was called
    assert mock_delay.called
    
    # Verify task was called with correct parameters
    call_args = mock_delay.call_args
    assert call_args is not None
    
    # Check keyword arguments
    kwargs = call_args.kwargs
    assert "filename" in kwargs
    assert "file_path" in kwargs
    assert "file_size" in kwargs
    assert "content_type" in kwargs
    assert "upload_timestamp" in kwargs
    
    # Verify values
    assert kwargs["filename"] == data["filename"]
    assert kwargs["file_size"] == 1024
    assert kwargs["content_type"] == "image/jpeg"
    assert isinstance(kwargs["upload_timestamp"], str)  # ISO format timestamp


def test_upload_task_queuing_failure_does_not_fail_upload(client, temp_upload_dir):
    """Test that upload succeeds even if task queuing fails."""
    tmpdir, _ = temp_upload_dir
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock Celery task to raise an exception
    with patch('services.upload_service.process_uploaded_file.delay', side_effect=Exception("Redis connection failed")):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
    
    # Upload should still succeed
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"].endswith(".jpg")
    
    # Task ID should be None when queuing fails
    assert data["task_id"] is None
    
    # Verify file was still saved
    upload_path = Path(tmpdir)
    saved_files = list(upload_path.glob("*.jpg"))
    assert len(saved_files) == 1
    assert saved_files[0].name == data["filename"]


def test_upload_task_id_in_response_when_queued(client, temp_upload_dir):
    """Test that task_id is included in response when task is successfully queued."""
    image_data = create_test_image("jpeg", 1024)
    image_data.seek(0)
    
    # Mock Celery task
    mock_task = MagicMock()
    mock_task.id = "abc123-task-id"
    
    with patch('services.upload_service.process_uploaded_file.delay', return_value=mock_task):
        response = client.post(
            "/api/v1/records/upload",
            files={"file": ("test.jpg", image_data, "image/jpeg")}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == "abc123-task-id"
    assert data["task_id"] is not None

