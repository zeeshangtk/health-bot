"""
Unit tests for GeminiService.
Tests image extraction, error handling, and response transformation.
"""
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from services.gemini_service import GeminiService


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing."""
    # Create a minimal valid JPEG image
    img = Image.new('RGB', (100, 100), color='red')
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img.save(tmp.name, 'JPEG')
        yield tmp.name
    # Cleanup
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def sample_gemini_response():
    """Sample Gemini API response matching expected structure."""
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
        "biochemistry_results": {
            "KIDNEY_FUNCTION_TEST": [
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
            ],
            "ELECTROLYTES": [
                {
                    "test_name": "Sodium",
                    "results": "140.0",
                    "unit": "mMol/L",
                    "reference_range": "136.0-145.0"
                }
            ]
        }
    }


@pytest.fixture
def gemini_service(mock_api_key):
    """Create a GeminiService instance with mocked API key."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": mock_api_key}):
        with patch('services.gemini_service.genai.configure'):
            with patch('services.gemini_service.genai.GenerativeModel'):
                service = GeminiService(api_key=mock_api_key)
                yield service


class TestGeminiServiceInit:
    """Tests for GeminiService initialization."""
    
    def test_init_with_api_key(self, mock_api_key):
        """Test initialization with provided API key."""
        with patch('services.gemini_service.genai.configure') as mock_configure:
            with patch('services.gemini_service.genai.GenerativeModel') as mock_model:
                service = GeminiService(api_key=mock_api_key)
                
                mock_configure.assert_called_once_with(api_key=mock_api_key)
                mock_model.assert_called_once_with('gemini-flash-latest')
                assert service.api_key == mock_api_key
    
    def test_init_with_settings(self, mock_api_key):
        """Test initialization with API key from settings."""
        with patch('services.gemini_service.settings') as mock_settings:
            mock_settings.gemini_api_key = mock_api_key
            with patch('services.gemini_service.genai.configure') as mock_configure:
                with patch('services.gemini_service.genai.GenerativeModel') as mock_model:
                    service = GeminiService()
                    
                    mock_configure.assert_called_once_with(api_key=mock_api_key)
                    mock_model.assert_called_once_with('gemini-flash-latest')
                    assert service.api_key == mock_api_key
    
    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch('services.gemini_service.settings') as mock_settings:
            mock_settings.gemini_api_key = ""
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiService()
    
    def test_init_sets_user_prompt(self, mock_api_key):
        """Test that user prompt is set correctly."""
        with patch('services.gemini_service.genai.configure'):
            with patch('services.gemini_service.genai.GenerativeModel'):
                service = GeminiService(api_key=mock_api_key)
                
                assert service.user_prompt is not None
                assert "hospital_info" in service.user_prompt
                assert "patient_info" in service.user_prompt
                assert "biochemistry_results" in service.user_prompt


class TestExtractLabReport:
    """Tests for extract_lab_report method."""
    
    def test_extract_lab_report_success(self, gemini_service, temp_image_file, sample_gemini_response):
        """Test successful lab report extraction."""
        # Mock the Gemini model response
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_gemini_response)
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        # Call the method
        result = gemini_service.extract_lab_report(temp_image_file)
        
        # Verify model was called with image and prompt
        mock_model_instance.generate_content.assert_called_once()
        call_args = mock_model_instance.generate_content.call_args[0][0]
        assert call_args[0] == gemini_service.user_prompt
        assert isinstance(call_args[1], Image.Image)
        
        # Verify result structure
        assert "hospital_info" in result
        assert "patient_info" in result
        assert "results" in result
        assert isinstance(result["results"], list)
        
        # Verify transformation (biochemistry_results -> results)
        assert len(result["results"]) == 3  # 2 from KIDNEY_FUNCTION_TEST + 1 from ELECTROLYTES
    
    def test_extract_lab_report_with_json_markdown(self, gemini_service, temp_image_file, sample_gemini_response):
        """Test extraction when Gemini returns JSON wrapped in markdown code blocks."""
        # Mock response with markdown code blocks
        json_text = json.dumps(sample_gemini_response)
        mock_response = MagicMock()
        mock_response.text = f"```json\n{json_text}\n```"
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        result = gemini_service.extract_lab_report(temp_image_file)
        
        assert "hospital_info" in result
        assert "results" in result
    
    def test_extract_lab_report_with_plain_json_markdown(self, gemini_service, temp_image_file, sample_gemini_response):
        """Test extraction when Gemini returns JSON wrapped in plain markdown code blocks."""
        json_text = json.dumps(sample_gemini_response)
        mock_response = MagicMock()
        mock_response.text = f"```\n{json_text}\n```"
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        result = gemini_service.extract_lab_report(temp_image_file)
        
        assert "hospital_info" in result
        assert "results" in result
    
    def test_extract_lab_report_file_not_found(self, gemini_service):
        """Test extraction when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            gemini_service.extract_lab_report("/nonexistent/file.jpg")
    
    def test_extract_lab_report_invalid_json_response(self, gemini_service, temp_image_file):
        """Test extraction when Gemini returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            gemini_service.extract_lab_report(temp_image_file)
    
    def test_extract_lab_report_api_error(self, gemini_service, temp_image_file):
        """Test extraction when Gemini API raises an error."""
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("API Error")
        gemini_service.model = mock_model_instance
        
        with pytest.raises(Exception, match="API Error"):
            gemini_service.extract_lab_report(temp_image_file)
    
    def test_extract_lab_report_empty_response(self, gemini_service, temp_image_file):
        """Test extraction when Gemini returns empty response."""
        mock_response = MagicMock()
        mock_response.text = ""
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            gemini_service.extract_lab_report(temp_image_file)


class TestTransformToLabReportFormat:
    """Tests for _transform_to_lab_report_format method."""
    
    def test_transform_with_multiple_categories(self, gemini_service, sample_gemini_response):
        """Test transformation with multiple test categories."""
        result = gemini_service._transform_to_lab_report_format(sample_gemini_response)
        
        assert "hospital_info" in result
        assert "patient_info" in result
        assert "results" in result
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 3  # 2 + 1 tests
    
    def test_transform_with_empty_categories(self, gemini_service):
        """Test transformation with empty biochemistry_results."""
        data = {
            "hospital_info": {"hospital_name": "Test", "report_type": "Lab"},
            "patient_info": {"patient_name": "Test"},
            "biochemistry_results": {}
        }
        
        result = gemini_service._transform_to_lab_report_format(data)
        
        assert result["results"] == []
    
    def test_transform_with_missing_fields(self, gemini_service):
        """Test transformation with missing optional fields provides defaults."""
        data = {
            "hospital_info": {},
            "patient_info": {},
            "biochemistry_results": {
                "CATEGORY": [
                    {"test_name": "Test", "results": "10", "unit": "mg/dl", "reference_range": "5-15"}
                ]
            }
        }
        
        result = gemini_service._transform_to_lab_report_format(data)
        
        # Required fields should have defaults when missing
        assert result["hospital_info"]["hospital_name"] == "Unknown"
        assert result["hospital_info"]["report_type"] == "Laboratory Reports"
        assert result["patient_info"]["patient_name"] == "Unknown Patient"
        assert result["patient_info"]["sample_date"] == "01-01-2025 12:00 AM"
        assert len(result["results"]) == 1
    
    def test_transform_with_non_list_category(self, gemini_service):
        """Test transformation when category value is not a list (should log warning)."""
        data = {
            "hospital_info": {"hospital_name": "Test"},
            "patient_info": {"patient_name": "Test"},
            "biochemistry_results": {
                "CATEGORY": "not a list"
            }
        }
        
        with patch('services.gemini_service.logger') as mock_logger:
            result = gemini_service._transform_to_lab_report_format(data)
            
            # Should log warning
            mock_logger.warning.assert_called()
            assert result["results"] == []
    
    def test_transform_preserves_all_test_fields(self, gemini_service, sample_gemini_response):
        """Test that all test fields are preserved in transformation."""
        result = gemini_service._transform_to_lab_report_format(sample_gemini_response)
        
        # Check first test result
        first_result = result["results"][0]
        assert "test_name" in first_result
        assert "results" in first_result
        assert "unit" in first_result
        assert "reference_range" in first_result
        assert first_result["test_name"] == "Blood Urea"
        assert first_result["results"] == "40.0"
        assert first_result["unit"] == "mg/dl"
        assert first_result["reference_range"] == "10.0-40.0"


class TestIntegration:
    """Integration tests for GeminiService."""
    
    def test_full_extraction_workflow(self, gemini_service, temp_image_file, sample_gemini_response):
        """Test complete extraction workflow from image to structured data."""
        # Mock the Gemini model response
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_gemini_response)
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        # Extract
        result = gemini_service.extract_lab_report(temp_image_file)
        
        # Verify complete structure
        assert result["hospital_info"]["hospital_name"] == "Test Hospital"
        assert result["patient_info"]["patient_name"] == "John Doe"
        assert len(result["results"]) == 3
        
        # Verify all tests are in flat list
        test_names = [r["test_name"] for r in result["results"]]
        assert "Blood Urea" in test_names
        assert "Creatinine" in test_names
        assert "Sodium" in test_names
    
    def test_extraction_with_real_image_structure(self, gemini_service, temp_image_file):
        """Test that image is properly opened and passed to Gemini."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "hospital_info": {"hospital_name": "Test"},
            "patient_info": {"patient_name": "Test"},
            "biochemistry_results": {}
        })
        
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        gemini_service.model = mock_model_instance
        
        # Extract
        gemini_service.extract_lab_report(temp_image_file)
        
        # Verify image was opened and passed
        call_args = mock_model_instance.generate_content.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0] == gemini_service.user_prompt
        assert isinstance(call_args[1], Image.Image)

