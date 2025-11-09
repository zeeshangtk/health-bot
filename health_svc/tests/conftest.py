"""
Shared pytest fixtures for API tests.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from storage.database import Database
from services.health_service import HealthService
from services.patient_service import PatientService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = Database(db_path=db_path)
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_app(temp_db):
    """Create a FastAPI test app with a temporary database."""
    app = FastAPI(title="Health Service API Test")
    
    # Create services with test database
    health_service = HealthService(db=temp_db)
    patient_service = PatientService(db=temp_db)
    
    # Import routers and create test versions with test services
    from fastapi import APIRouter, HTTPException, Query
    from typing import Optional, List
    from api.schemas import (
        HealthRecordCreate,
        HealthRecordResponse,
        PatientCreate,
        PatientResponse
    )
    
    # Create test routers
    health_router = APIRouter()
    patients_router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])
    records_router = APIRouter(prefix="/api/v1/records", tags=["Health Records"])
    
    # Health router
    @health_router.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Health Service API", "version": "1.0.0"}
    
    # Patients router
    @patients_router.post("", response_model=PatientResponse, status_code=201)
    async def create_patient(patient: PatientCreate):
        """Create a new patient."""
        result = patient_service.add_patient(patient.name)
        if not result["success"]:
            raise HTTPException(status_code=409, detail=result["message"])
        return result["patient"]
    
    @patients_router.get("", response_model=List[PatientResponse])
    async def list_patients():
        """Get all patients, sorted alphabetically."""
        return patient_service.get_patients()
    
    # Records router
    @records_router.post("", response_model=HealthRecordResponse, status_code=201)
    async def create_record(record: HealthRecordCreate):
        """Create a new health record."""
        result = health_service.save_record(
            timestamp=record.timestamp,
            patient=record.patient,
            record_type=record.record_type,
            data_type=record.data_type,
            value=record.value
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result["record"]
    
    @records_router.get("", response_model=List[HealthRecordResponse])
    async def list_records(
        patient: Optional[str] = Query(None, description="Filter by patient name"),
        record_type: Optional[str] = Query(None, description="Filter by record type"),
        limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results")
    ):
        """Get health records with optional filters."""
        records = health_service.get_records(
            patient=patient,
            record_type=record_type,
            limit=limit
        )
        return records
    
    # Include all routers
    app.include_router(health_router)
    app.include_router(patients_router)
    app.include_router(records_router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the API."""
    return TestClient(test_app)

