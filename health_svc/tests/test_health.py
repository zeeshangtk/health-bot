"""
Tests for health/root endpoint.
"""
# Root Endpoint Tests
def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Health Service API"
    assert data["version"] == "1.0.0"

