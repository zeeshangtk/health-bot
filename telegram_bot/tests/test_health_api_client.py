"""
Unit tests for health_api_client.
Tests that the HTTP client correctly interacts with the Health Service API.
"""
import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime
import httpx

from clients.health_api_client import HealthAPIClient, get_health_api_client


# Sample test data
TEST_PATIENT_NAME = "Nazra Mastoor"
TEST_PATIENT_RESPONSE = {
    "id": 1,
    "name": TEST_PATIENT_NAME,
    "created_at": "2025-01-01 10:00:00"
}

TEST_RECORD = {
    "timestamp": "2025-01-01T10:00:00",
    "patient": TEST_PATIENT_NAME,
    "record_type": "BP",
    "data_type": "text",
    "value": "120/80"
}


@pytest.fixture
def mock_client():
    """Create a HealthAPIClient with a test base URL."""
    return HealthAPIClient(base_url="http://test-server")


@pytest.mark.asyncio
async def test_get_patients_success(mock_client):
    """Test successful get_patients call."""
    mock_response = [TEST_PATIENT_RESPONSE]
    
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        result = await mock_client.get_patients()
        
        assert len(result) == 1
        assert result[0]["name"] == TEST_PATIENT_NAME
        assert result[0]["id"] == 1
        mock_request.assert_called_once_with("GET", "/api/v1/patients")


@pytest.mark.asyncio
async def test_get_patients_empty(mock_client):
    """Test get_patients with empty result."""
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = []
        
        result = await mock_client.get_patients()
        
        assert result == []
        assert isinstance(result, list)
        mock_request.assert_called_once_with("GET", "/api/v1/patients")


@pytest.mark.asyncio
async def test_get_patients_connection_error(mock_client):
    """Test get_patients with connection error."""
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            await mock_client.get_patients()


@pytest.mark.asyncio
async def test_add_patient_success(mock_client):
    """Test successful add_patient call."""
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = TEST_PATIENT_RESPONSE
        
        result = await mock_client.add_patient(TEST_PATIENT_NAME)
        
        assert result["name"] == TEST_PATIENT_NAME
        assert result["id"] == 1
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once_with(
            "POST",
            "/api/v1/patients",
            json={"name": TEST_PATIENT_NAME}
        )


@pytest.mark.asyncio
async def test_add_patient_duplicate(mock_client):
    """Test add_patient with duplicate patient (409 error)."""
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ValueError("API error 409: Patient already exists")
        
        with pytest.raises(ValueError) as exc_info:
            await mock_client.add_patient(TEST_PATIENT_NAME)
        
        assert "409" in str(exc_info.value) or "already exists" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_save_record_success(mock_client):
    """Test successful save_record call."""
    timestamp = datetime(2025, 1, 1, 10, 0, 0)
    
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = TEST_RECORD
        
        result = await mock_client.save_record(
            timestamp=timestamp,
            patient=TEST_PATIENT_NAME,
            record_type="BP",
            data_type="text",
            value="120/80"
        )
        
        assert result["patient"] == TEST_PATIENT_NAME
        assert result["record_type"] == "BP"
        assert result["value"] == "120/80"
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once_with(
            "POST",
            "/api/v1/records",
            json={
                "timestamp": timestamp.isoformat(),
                "patient": TEST_PATIENT_NAME,
                "record_type": "BP",
                "data_type": "text",
                "value": "120/80"
            }
        )


@pytest.mark.asyncio
async def test_save_record_patient_not_found(mock_client):
    """Test save_record with patient not found (400 error)."""
    timestamp = datetime(2025, 1, 1, 10, 0, 0)
    
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ValueError("API error 400: Patient not found")
        
        with pytest.raises(ValueError) as exc_info:
            await mock_client.save_record(
                timestamp=timestamp,
                patient="NonExistent",
                record_type="BP",
                data_type="text",
                value="120/80"
            )
        
        assert "400" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_records_all(mock_client):
    """Test get_records without filters."""
    mock_records = [TEST_RECORD]
    
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_records
        
        result = await mock_client.get_records()
        
        assert len(result) == 1
        assert result[0]["patient"] == TEST_PATIENT_NAME
        
        # Verify request was made without params
        mock_request.assert_called_once_with("GET", "/api/v1/records", params={})


@pytest.mark.asyncio
async def test_get_records_with_filters(mock_client):
    """Test get_records with patient and record_type filters."""
    mock_records = [TEST_RECORD]
    
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_records
        
        result = await mock_client.get_records(
            patient=TEST_PATIENT_NAME,
            record_type="BP",
            limit=5
        )
        
        assert len(result) == 1
        
        # Verify request was made with correct params
        mock_request.assert_called_once_with(
            "GET",
            "/api/v1/records",
            params={
                "patient": TEST_PATIENT_NAME,
                "record_type": "BP",
                "limit": 5
            }
        )


@pytest.mark.asyncio
async def test_get_records_connection_error(mock_client):
    """Test get_records with connection error."""
    with patch.object(mock_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            await mock_client.get_records()


def test_get_health_api_client_singleton():
    """Test that get_health_api_client returns a singleton."""
    # Reset the global instance
    import clients.health_api_client
    clients.health_api_client._client_instance = None
    
    with patch("clients.health_api_client.HealthAPIClient") as mock_client_class:
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        client1 = get_health_api_client()
        client2 = get_health_api_client()
        
        # Should return the same instance
        assert client1 is client2
        # Should only create one instance
        assert mock_client_class.call_count == 1


def test_health_api_client_init_with_base_url():
    """Test HealthAPIClient initialization with custom base URL."""
    client = HealthAPIClient(base_url="http://custom-server:8080")
    assert client.base_url == "http://custom-server:8080"


def test_health_api_client_init_removes_trailing_slash():
    """Test that HealthAPIClient removes trailing slash from base URL."""
    client = HealthAPIClient(base_url="http://test-server/")
    assert client.base_url == "http://test-server"


def test_health_api_client_init_requires_url():
    """Test that HealthAPIClient raises error if no URL provided."""
    with patch("clients.health_api_client.HEALTH_SVC_API_URL", None):
        with pytest.raises(ValueError, match="HEALTH_SVC_API_URL"):
            HealthAPIClient()
