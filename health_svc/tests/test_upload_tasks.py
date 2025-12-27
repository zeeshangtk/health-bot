"""
Unit tests for upload_tasks module.
Tests the process_uploaded_file Celery task.
"""
import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, Mock
from PIL import Image

from tasks.upload_tasks import (
    process_uploaded_file,
    LabReport,
    HospitalInfo,
    PatientInfo,
    TestResult,
    parse_sample_date
)
from storage.database import Database

# For testing Celery tasks, we'll call the .run() method directly
# which properly handles the bound task signature
def call_process_uploaded_file(task_self, filename, file_path, file_size, content_type, upload_timestamp):
    """Helper to call the Celery task function directly for testing."""
    return process_uploaded_file.run(filename, file_path, file_size, content_type, upload_timestamp)


@pytest.fixture
def temp_file():
    """Create a temporary image file for testing."""
    # Create a minimal valid JPEG image
    img = Image.new('RGB', (100, 100), color='red')
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img.save(tmp.name, 'JPEG')
        file_path = tmp.name
        file_size = os.path.getsize(file_path)
        yield file_path, file_size
    # Cleanup
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def sample_lab_report_data():
    """Sample lab report data matching LabReport structure."""
    return {
        "hospital_info": {
            "hospital_name": "Test Hospital",
            "report_type": "Laboratory Reports"
        },
        "patient_info": {
            "patient_name": "John Doe",
            "patient_id": "PAT12345",
            "age_sex": "45Y / MALE",
            "sample_date": "15-12-2024 10:30 AM",
            "referring_doctor_full_name_titles": "DR. Jane Smith MBBS, MD"
        },
        "results": [
            {
                "test_name": "Blood Urea",
                "results": "40.0",
                "unit": "mg/dl",
                "reference_range": "10.0-40.0"
            },
            {
                "test_name": "Creatinine",
                "results": "1.0",
                "unit": "mg/dl",
                "reference_range": "0.8-1.2"
            }
        ]
    }


@pytest.fixture
def mock_database():
    """Create a mock database for testing."""
    db = MagicMock(spec=Database)
    db.save_lab_report_records.return_value = [1, 2]  # Return record IDs
    return db


@pytest.fixture
def mock_task():
    """Create a mock Celery task instance."""
    task = Mock()
    task.request.retries = 0
    task.retry = Mock(side_effect=Exception("Retry called"))
    return task


class TestParseSampleDate:
    """Tests for parse_sample_date function."""
    
    def test_parse_valid_date(self):
        """Test parsing a valid date string."""
        date_str = "15-12-2024 10:30 AM"
        result = parse_sample_date(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
    
    def test_parse_date_pm(self):
        """Test parsing a date with PM."""
        date_str = "15-12-2024 02:30 PM"
        result = parse_sample_date(date_str)
        
        assert result.hour == 14  # 2 PM = 14:00

    def test_parse_midnight_am(self):
        """Test parsing '00:00 AM' which Gemini sometimes returns."""
        date_str = "28-09-2025 00:00 AM"
        result = parse_sample_date(date_str)
        
        assert result.hour == 0
        assert result.minute == 0
        assert result.day == 28
        assert result.month == 9
        assert result.year == 2025
    
    def test_parse_invalid_date_format(self):
        """Test parsing an invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse sample date"):
            parse_sample_date("2024-12-15 10:30")
    
    def test_parse_invalid_date_value(self):
        """Test parsing an invalid date value raises ValueError."""
        with pytest.raises(ValueError):
            parse_sample_date("32-12-2024 10:30 AM")


class TestProcessUploadedFile:
    """Tests for process_uploaded_file Celery task."""
    
    def test_process_uploaded_file_success(
        self, mock_task, temp_file, sample_lab_report_data, mock_database
    ):
        """Test successful file processing."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Mock GeminiService
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = sample_lab_report_data
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success",
            "id": 123
        }
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    result = call_process_uploaded_file(
                        mock_task,
                        filename,
                        file_path,
                        file_size,
                        content_type,
                        upload_timestamp
                    )
        
        # Verify result
        assert result["status"] == "success"
        assert result["filename"] == filename
        assert result["file_path"] == file_path
        assert result["file_size"] == file_size
        assert result["content_type"] == content_type
        assert result["upload_timestamp"] == upload_timestamp
        assert result["lab_report"] == sample_lab_report_data
        assert result["records_saved"] == 2
        
        # Verify GeminiService was called
        mock_gemini_service.extract_lab_report.assert_called_once_with(file_path)
        
        # Verify PaperlessNgxService was called
        mock_paperless_service.upload_medical_document_from_dict.assert_called_once_with(
            document_path=file_path,
            medical_info=sample_lab_report_data
        )
        
        # Verify database was called
        mock_database.save_lab_report_records.assert_called_once()
        call_kwargs = mock_database.save_lab_report_records.call_args[1]
        assert call_kwargs["patient_name"] == "John Doe"
        assert call_kwargs["lab_name"] == "Test Hospital"
        assert len(call_kwargs["test_results"]) == 2
    
    def test_process_uploaded_file_not_found(self, mock_task):
        """Test processing when file doesn't exist."""
        filename = "nonexistent.jpg"
        file_path = "/nonexistent/path/file.jpg"
        file_size = 1024
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        with pytest.raises(FileNotFoundError):
            call_process_uploaded_file(
                mock_task,
                filename,
                file_path,
                file_size,
                content_type,
                upload_timestamp
            )
    
    def test_process_uploaded_file_size_mismatch(
        self, mock_task, temp_file, sample_lab_report_data, mock_database
    ):
        """Test processing when file size doesn't match (should log warning but continue)."""
        file_path, actual_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        reported_size = actual_size + 100  # Mismatch
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = sample_lab_report_data
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    with patch('tasks.upload_tasks.logger') as mock_logger:
                        result = call_process_uploaded_file(
                            mock_task,
                            filename,
                            file_path,
                            reported_size,
                            content_type,
                            upload_timestamp
                        )
        
        # Should still succeed but log warning
        assert result["status"] == "success"
        mock_logger.warning.assert_called()
    
    def test_process_uploaded_file_gemini_extraction_failure(
        self, mock_task, temp_file
    ):
        """Test processing when Gemini extraction fails."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Mock GeminiService to raise exception
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.side_effect = Exception("Gemini API Error")
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.logger') as mock_logger:
                with pytest.raises(Exception, match="Gemini API Error"):
                    call_process_uploaded_file(
                        mock_task,
                        filename,
                        file_path,
                        file_size,
                        content_type,
                        upload_timestamp
                    )
        
        # Should log error
        mock_logger.error.assert_called()
    
    def test_process_uploaded_file_invalid_lab_report_structure(
        self, mock_task, temp_file, mock_database
    ):
        """Test processing when lab report structure is invalid."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Invalid lab report (missing required fields)
        invalid_lab_report = {
            "hospital_info": {},
            "patient_info": {},
            "results": []
        }
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = invalid_lab_report
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    with patch('tasks.upload_tasks.logger') as mock_logger:
                        # Should raise validation error when creating LabReport
                        with pytest.raises(Exception):
                            call_process_uploaded_file(
                                mock_task,
                                filename,
                                file_path,
                                file_size,
                                content_type,
                                upload_timestamp
                            )
        
        mock_logger.error.assert_called()
    
    def test_process_uploaded_file_invalid_date_format(
        self, mock_task, temp_file, mock_database
    ):
        """Test processing when sample date format is invalid."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Lab report with invalid date format
        lab_report = {
            "hospital_info": {
                "hospital_name": "Test Hospital",
                "report_type": "Laboratory Reports"
            },
            "patient_info": {
                "patient_name": "John Doe",
                "patient_id": "PAT12345",
                "age_sex": "45Y / MALE",
                "sample_date": "2024-12-15 10:30",  # Invalid format
                "referring_doctor_full_name_titles": "DR. Jane Smith"
            },
            "results": []
        }
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = lab_report
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    with patch('tasks.upload_tasks.logger') as mock_logger:
                        with pytest.raises(ValueError):
                            call_process_uploaded_file(
                                mock_task,
                                filename,
                                file_path,
                                file_size,
                                content_type,
                                upload_timestamp
                            )
        
        mock_logger.error.assert_called()
    
    def test_process_uploaded_file_database_save_failure(
        self, mock_task, temp_file, sample_lab_report_data
    ):
        """Test processing when database save fails."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = sample_lab_report_data
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        # Mock database to raise exception
        mock_database = MagicMock()
        mock_database.save_lab_report_records.side_effect = Exception("Database Error")
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    with patch('tasks.upload_tasks.logger') as mock_logger:
                        with pytest.raises(Exception, match="Database Error"):
                            call_process_uploaded_file(
                                mock_task,
                                filename,
                                file_path,
                                file_size,
                                content_type,
                                upload_timestamp
                            )
        
        mock_logger.error.assert_called()
    
    def test_process_uploaded_file_retry_on_general_exception(
        self, mock_task, temp_file
    ):
        """Test that general exceptions trigger retry mechanism."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Mock GeminiService to raise exception
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.side_effect = Exception("General Error")
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with pytest.raises(Exception):
                # Should call retry
                try:
                    call_process_uploaded_file(
                        mock_task,
                        filename,
                        file_path,
                        file_size,
                        content_type,
                        upload_timestamp
                    )
                except Exception:
                    # Verify retry was called
                    assert mock_task.retry.called
    
    def test_process_uploaded_file_no_retry_on_file_not_found(
        self, mock_task
    ):
        """Test that FileNotFoundError doesn't trigger retry."""
        filename = "nonexistent.jpg"
        file_path = "/nonexistent/path/file.jpg"
        file_size = 1024
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        with pytest.raises(FileNotFoundError):
            call_process_uploaded_file(
                mock_task,
                filename,
                file_path,
                file_size,
                content_type,
                upload_timestamp
            )
        
        # Retry should not be called for FileNotFoundError
        assert not mock_task.retry.called
    
    def test_process_uploaded_file_empty_results(
        self, mock_task, temp_file, mock_database
    ):
        """Test processing with empty test results."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        lab_report = {
            "hospital_info": {
                "hospital_name": "Test Hospital",
                "report_type": "Laboratory Reports"
            },
            "patient_info": {
                "patient_name": "John Doe",
                "patient_id": "PAT12345",
                "age_sex": "45Y / MALE",
                "sample_date": "15-12-2024 10:30 AM",
                "referring_doctor_full_name_titles": "DR. Jane Smith"
            },
            "results": []  # Empty results
        }
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = lab_report
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        mock_database.save_lab_report_records.return_value = []  # No records saved
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    result = call_process_uploaded_file(
                        mock_task,
                        filename,
                        file_path,
                        file_size,
                        content_type,
                        upload_timestamp
                    )
        
        assert result["status"] == "success"
        assert result["records_saved"] == 0
        mock_database.save_lab_report_records.assert_called_once()
        call_kwargs = mock_database.save_lab_report_records.call_args[1]
        assert call_kwargs["test_results"] == []
    
    def test_process_uploaded_file_test_results_extraction(
        self, mock_task, temp_file, sample_lab_report_data, mock_database
    ):
        """Test that test results are correctly extracted and passed to database."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = sample_lab_report_data
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    call_process_uploaded_file(
                        mock_task,
                        filename,
                        file_path,
                        file_size,
                        content_type,
                        upload_timestamp
                    )
        
        # Verify test_results structure
        call_kwargs = mock_database.save_lab_report_records.call_args[1]
        test_results = call_kwargs["test_results"]
        
        assert len(test_results) == 2
        assert test_results[0]["test_name"] == "Blood Urea"
        assert test_results[0]["results"] == "40.0"
        assert test_results[0]["unit"] == "mg/dl"
        assert "reference_range" not in test_results[0]  # Should be excluded
    
    def test_process_uploaded_file_timestamp_parsing(
        self, mock_task, temp_file, mock_database
    ):
        """Test that sample date is correctly parsed to datetime."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        lab_report = {
            "hospital_info": {
                "hospital_name": "Test Hospital",
                "report_type": "Laboratory Reports"
            },
            "patient_info": {
                "patient_name": "John Doe",
                "patient_id": "PAT12345",
                "age_sex": "45Y / MALE",
                "sample_date": "15-12-2024 10:30 AM",
                "referring_doctor_full_name_titles": "DR. Jane Smith"
            },
            "results": []
        }
        
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = lab_report
        
        # Mock PaperlessNgxService
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.return_value = {
            "status": "success"
        }
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    call_process_uploaded_file(
                        mock_task,
                        filename,
                        file_path,
                        file_size,
                        content_type,
                        upload_timestamp
                    )
        
        # Verify timestamp was parsed correctly
        call_kwargs = mock_database.save_lab_report_records.call_args[1]
        timestamp = call_kwargs["timestamp"]
        
        assert isinstance(timestamp, datetime)
        assert timestamp.year == 2024
        assert timestamp.month == 12
        assert timestamp.day == 15
        assert timestamp.hour == 10
        assert timestamp.minute == 30
    
    def test_process_uploaded_file_paperless_ngx_failure(
        self, mock_task, temp_file, sample_lab_report_data, mock_database
    ):
        """Test that Paperless NGX upload failure doesn't break the task."""
        file_path, file_size = temp_file
        filename = Path(file_path).name
        content_type = "image/jpeg"
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Mock GeminiService
        mock_gemini_service = MagicMock()
        mock_gemini_service.extract_lab_report.return_value = sample_lab_report_data
        
        # Mock PaperlessNgxService to raise exception
        mock_paperless_service = MagicMock()
        mock_paperless_service.upload_medical_document_from_dict.side_effect = Exception("Paperless NGX Error")
        
        with patch('tasks.upload_tasks.GeminiService', return_value=mock_gemini_service):
            with patch('tasks.upload_tasks.PaperlessNgxService', return_value=mock_paperless_service):
                with patch('tasks.upload_tasks.get_database', return_value=mock_database):
                    with patch('tasks.upload_tasks.logger') as mock_logger:
                        result = call_process_uploaded_file(
                            mock_task,
                            filename,
                            file_path,
                            file_size,
                            content_type,
                            upload_timestamp
                        )
        
        # Task should still succeed
        assert result["status"] == "success"
        assert result["records_saved"] == 2
        
        # Should log warning about Paperless NGX failure
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                         if "Paperless NGX" in str(call)]
        assert len(warning_calls) > 0
        
        # Database should still be called
        mock_database.save_lab_report_records.assert_called_once()
