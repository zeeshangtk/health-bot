"""
Tests for health, readiness, and metrics endpoints.

These tests verify the observability endpoints work correctly:
- /health: Liveness probe
- /ready: Readiness probe with dependency checks
- /metrics: Prometheus-format metrics
- /: Root endpoint with API info
"""


# =============================================================================
# ROOT ENDPOINT TESTS
# =============================================================================

def test_root_endpoint(client):
    """Test the root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    # New format uses "service" instead of "message"
    assert data["service"] == "Health Service API"
    assert data["version"] == "1.0.0"
    # Verify links to other endpoints
    assert "health" in data
    assert "ready" in data
    assert "metrics" in data


# =============================================================================
# HEALTH ENDPOINT TESTS (LIVENESS)
# =============================================================================

def test_health_endpoint(client):
    """Test the /health liveness endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


# =============================================================================
# READINESS ENDPOINT TESTS
# =============================================================================

def test_ready_endpoint(client):
    """Test the /ready readiness endpoint."""
    response = client.get("/ready")
    # Should return 200 if dependencies are healthy
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ready", "degraded", "not_ready")
    assert "dependencies" in data
    assert "timestamp" in data
    
    # Check that dependencies have expected structure
    for dep in data["dependencies"]:
        assert "name" in dep
        assert "status" in dep


# =============================================================================
# METRICS ENDPOINT TESTS
# =============================================================================

def test_metrics_endpoint(client):
    """Test the /metrics Prometheus endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Check content type is Prometheus text format
    assert "text/plain" in response.headers.get("content-type", "")
    # Check response contains expected metric names
    content = response.text
    assert "http_requests_total" in content
    assert "http_request_duration_ms" in content


def test_metrics_json_endpoint(client):
    """Test the /metrics/json endpoint."""
    response = client.get("/metrics/json")
    assert response.status_code == 200
    data = response.json()
    # Check expected fields exist
    assert "http_requests_total" in data
    assert "http_requests_2xx_total" in data
    assert "http_requests_4xx_total" in data
    assert "http_requests_5xx_total" in data
    assert "http_request_duration_ms_p50" in data
    assert "http_request_duration_ms_p95" in data

