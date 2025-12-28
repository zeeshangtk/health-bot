"""
Shared pytest fixtures for API tests.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from repositories.base import Database
from repositories import PatientRepository, HealthRecordRepository
from services.health_service import HealthService
from services.patient_service import PatientService
from services.graph import GraphService


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
    
    # Create repositories with test database
    patient_repo = PatientRepository(db=temp_db)
    record_repo = HealthRecordRepository(db=temp_db)
    
    # Create services with test repositories
    health_service = HealthService(
        patient_repository=patient_repo,
        health_record_repository=record_repo
    )
    patient_service = PatientService(patient_repository=patient_repo)
    graph_service = GraphService()
    
    # Import routers and create test versions with test services
    from fastapi import APIRouter, HTTPException, Query, Response
    from typing import Optional, List
    from schemas import (
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
            value=record.value,
            unit=record.unit,
            lab_name=record.lab_name
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
    
    @records_router.get("/html-view")
    async def get_html_view(
        patient_name: str = Query(..., description="Patient name to generate graph for")
    ):
        """Get HTML graph view of patient health records."""
        records = health_service.get_records(patient=patient_name)
        html_content = graph_service.generate_html_graph(records, patient_name)
        return Response(content=html_content, media_type="text/html")
    
    # Include all routers
    app.include_router(health_router)
    app.include_router(patients_router)
    app.include_router(records_router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the API."""
    return TestClient(test_app)
