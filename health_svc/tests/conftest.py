"""
Shared pytest fixtures for API tests.

This module provides test fixtures that work with the new dependency injection
architecture. Key patterns:

1. Database Isolation: Each test gets a fresh temporary database
2. DI Override: Use app.dependency_overrides to inject test dependencies
3. Service Injection: Services are created with test repositories

Fixture Hierarchy:
    temp_db → repositories → services → test_app → client
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Set test API key before importing config modules
# This must happen before any config imports
TEST_API_KEY = "test-api-key-for-testing-purposes-12345678"
os.environ.setdefault("HEALTH_SVC_API_KEY", TEST_API_KEY)

from repositories.base import Database
from repositories import PatientRepository, HealthRecordRepository
from services.health_service import HealthService
from services.patient_service import PatientService
from services.graph import GraphService
from core.exceptions import setup_exception_handlers
from core import dependencies as deps
from core.auth import verify_api_key


@pytest.fixture
def temp_db():
    """
    Create a temporary database for testing.
    
    This fixture creates a fresh SQLite database in a temp file,
    ensuring complete isolation between tests.
    """
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = Database(db_path=db_path)
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def patient_repo(temp_db):
    """Create a PatientRepository with the test database."""
    return PatientRepository(db=temp_db)


@pytest.fixture
def record_repo(temp_db):
    """Create a HealthRecordRepository with the test database."""
    return HealthRecordRepository(db=temp_db)


@pytest.fixture
def patient_service(patient_repo):
    """Create a PatientService with the test repository."""
    return PatientService(patient_repository=patient_repo)


@pytest.fixture
def health_service(patient_repo, record_repo):
    """Create a HealthService with test repositories."""
    return HealthService(
        patient_repository=patient_repo,
        health_record_repository=record_repo
    )


@pytest.fixture
def graph_service():
    """Create a GraphService instance."""
    return GraphService()


@pytest.fixture
def test_app(temp_db, patient_repo, record_repo, patient_service, health_service, graph_service):
    """
    Create a FastAPI test app with dependency overrides.
    
    This fixture creates a full FastAPI app and overrides the DI dependencies
    to use test instances. This approach:
    - Uses the real routers (testing actual endpoint code)
    - Injects test database and services via dependency_overrides
    - Registers exception handlers for proper error response testing
    """
    from api.routers import health_router, patients_router, records_router
    
    app = FastAPI(title="Health Service API Test")
    
    # Register exception handlers (same as production)
    setup_exception_handlers(app)
    
    # Override dependencies to use test instances
    # This is the key to testing with DI - we replace the production
    # dependency functions with ones that return our test instances
    app.dependency_overrides[deps.get_database] = lambda: temp_db
    app.dependency_overrides[deps.get_patient_repository] = lambda: patient_repo
    app.dependency_overrides[deps.get_health_record_repository] = lambda: record_repo
    app.dependency_overrides[deps.get_patient_service] = lambda: patient_service
    app.dependency_overrides[deps.get_health_service] = lambda: health_service
    app.dependency_overrides[deps.get_graph_service] = lambda: graph_service
    
    # Override auth to skip API key verification in tests
    # This allows tests to run without providing API key headers
    async def skip_auth():
        return TEST_API_KEY
    app.dependency_overrides[verify_api_key] = skip_auth
    
    # Include the real routers (not test copies)
    app.include_router(health_router)
    app.include_router(patients_router)
    app.include_router(records_router)
    
    yield app
    
    # Cleanup: Clear dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Create a test client for the API."""
    return TestClient(test_app)
