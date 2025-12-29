"""
Tests for API authentication.
"""
import os
import pytest
from fastapi.testclient import TestClient

# Set test API key before importing app
TEST_API_KEY = "test-api-key-for-testing-purposes-12345678"
os.environ["HEALTH_SVC_API_KEY"] = TEST_API_KEY


@pytest.fixture
def authenticated_client():
    """Create a test client with authenticated routers."""
    from main import app
    return TestClient(app)


class TestAuthentication:
    """Test suite for API authentication."""
    
    def test_missing_api_key_returns_401(self, authenticated_client):
        """Test that requests without API key return 401."""
        response = authenticated_client.get("/api/v1/patients")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]
    
    def test_invalid_api_key_returns_403(self, authenticated_client):
        """Test that requests with invalid API key return 403."""
        response = authenticated_client.get(
            "/api/v1/patients",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]
    
    def test_valid_api_key_allows_access(self, authenticated_client):
        """Test that requests with valid API key are allowed."""
        response = authenticated_client.get(
            "/api/v1/patients",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
    
    def test_health_endpoint_no_auth_required(self, authenticated_client):
        """Test that the health/root endpoint doesn't require authentication."""
        response = authenticated_client.get("/")
        assert response.status_code == 200
        assert "Health Service API" in response.json()["message"]
    
    def test_patients_create_requires_auth(self, authenticated_client):
        """Test that creating patients requires authentication."""
        import uuid
        unique_name = f"Test Patient {uuid.uuid4().hex[:8]}"
        
        # Without API key
        response = authenticated_client.post(
            "/api/v1/patients",
            json={"name": unique_name}
        )
        assert response.status_code == 401
        
        # With valid API key
        response = authenticated_client.post(
            "/api/v1/patients",
            json={"name": unique_name},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 201
    
    def test_records_create_requires_auth(self, authenticated_client):
        """Test that creating records requires authentication."""
        import uuid
        unique_name = f"Auth Test Patient {uuid.uuid4().hex[:8]}"
        
        # First create a patient
        authenticated_client.post(
            "/api/v1/patients",
            json={"name": unique_name},
            headers={"X-API-Key": TEST_API_KEY}
        )
        
        # Without API key
        response = authenticated_client.post(
            "/api/v1/records",
            json={
                "timestamp": "2025-01-01T10:00:00",
                "patient": unique_name,
                "record_type": "BP",
                "value": "120/80"
            }
        )
        assert response.status_code == 401
        
        # With valid API key
        response = authenticated_client.post(
            "/api/v1/records",
            json={
                "timestamp": "2025-01-01T10:00:00",
                "patient": unique_name,
                "record_type": "BP",
                "value": "120/80"
            },
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 201
    
    def test_records_list_requires_auth(self, authenticated_client):
        """Test that listing records requires authentication."""
        response = authenticated_client.get("/api/v1/records")
        assert response.status_code == 401
        
        response = authenticated_client.get(
            "/api/v1/records",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
    
    def test_html_view_requires_auth(self, authenticated_client):
        """Test that HTML view requires authentication."""
        response = authenticated_client.get(
            "/api/v1/records/html-view",
            params={"patient_name": "Test Patient"}
        )
        assert response.status_code == 401
        
        response = authenticated_client.get(
            "/api/v1/records/html-view",
            params={"patient_name": "Test Patient"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200

