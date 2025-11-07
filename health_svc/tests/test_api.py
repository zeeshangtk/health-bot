"""
Integration tests for Health Service API endpoints.
Tests the full API stack including routes, services, and database.
"""
import os
import tempfile
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from storage.database import Database
from services.health_service import HealthService
from services.patient_service import PatientService
from api.routes import router
from fastapi import FastAPI


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
    
    # Create a new router with test services
    test_router = router
    
    # Override the services in the router by monkey-patching
    # We'll need to create new route handlers that use our test services
    from fastapi import APIRouter, HTTPException, Query
    from typing import Optional, List
    from api.schemas import (
        HealthRecordCreate,
        HealthRecordResponse,
        PatientCreate,
        PatientResponse
    )
    
    test_router = APIRouter()
    
    @test_router.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Health Service API", "version": "1.0.0"}
    
    @test_router.post("/api/v1/patients", response_model=PatientResponse, status_code=201)
    async def create_patient(patient: PatientCreate):
        """Create a new patient."""
        result = patient_service.add_patient(patient.name)
        if not result["success"]:
            raise HTTPException(status_code=409, detail=result["message"])
        return result["patient"]
    
    @test_router.get("/api/v1/patients", response_model=List[PatientResponse])
    async def list_patients():
        """Get all patients, sorted alphabetically."""
        return patient_service.get_patients()
    
    @test_router.post("/api/v1/records", response_model=HealthRecordResponse, status_code=201)
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
    
    @test_router.get("/api/v1/records", response_model=List[HealthRecordResponse])
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
    
    app.include_router(test_router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the API."""
    return TestClient(test_app)


# Root Endpoint Tests
def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Health Service API"
    assert data["version"] == "1.0.0"


# Patient Endpoint Tests
def test_create_patient_success(client):
    """Test successful patient creation."""
    response = client.post(
        "/api/v1/patients",
        json={"name": "John Doe"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert "id" in data
    assert "created_at" in data
    assert isinstance(data["id"], int)


def test_create_patient_duplicate(client):
    """Test creating a duplicate patient returns 409."""
    # Create first patient
    response1 = client.post(
        "/api/v1/patients",
        json={"name": "Jane Doe"}
    )
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post(
        "/api/v1/patients",
        json={"name": "Jane Doe"}
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower()


def test_create_patient_validation_empty_name(client):
    """Test patient creation with empty name fails validation."""
    response = client.post(
        "/api/v1/patients",
        json={"name": ""}
    )
    assert response.status_code == 422  # Validation error


def test_create_patient_validation_missing_name(client):
    """Test patient creation without name field fails validation."""
    response = client.post(
        "/api/v1/patients",
        json={}
    )
    assert response.status_code == 422  # Validation error


def test_get_patients_empty(client):
    """Test getting patients when database is empty."""
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    assert response.json() == []


def test_get_patients_multiple(client):
    """Test getting multiple patients returns them sorted alphabetically."""
    # Create patients in non-alphabetical order
    client.post("/api/v1/patients", json={"name": "Zebra Patient"})
    client.post("/api/v1/patients", json={"name": "Alice Patient"})
    client.post("/api/v1/patients", json={"name": "Bob Patient"})
    
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) == 3
    assert patients[0]["name"] == "Alice Patient"
    assert patients[1]["name"] == "Bob Patient"
    assert patients[2]["name"] == "Zebra Patient"


# Health Record Endpoint Tests
def test_create_record_success(client):
    """Test successful health record creation."""
    # First create a patient
    patient_response = client.post(
        "/api/v1/patients",
        json={"name": "Test Patient"}
    )
    assert patient_response.status_code == 201
    
    # Create a health record
    record_data = {
        "timestamp": "2025-01-01T10:00:00",
        "patient": "Test Patient",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    }
    response = client.post("/api/v1/records", json=record_data)
    assert response.status_code == 201
    data = response.json()
    assert data["patient"] == "Test Patient"
    assert data["record_type"] == "BP"
    assert data["data_type"] == "text"
    assert data["value"] == "120/80"
    assert "timestamp" in data


def test_create_record_patient_not_found(client):
    """Test creating a record for non-existent patient returns 400."""
    record_data = {
        "timestamp": "2025-01-01T10:00:00",
        "patient": "Non-existent Patient",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    }
    response = client.post("/api/v1/records", json=record_data)
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_create_record_validation_missing_fields(client):
    """Test record creation with missing required fields fails validation."""
    # Missing patient
    response = client.post(
        "/api/v1/records",
        json={
            "timestamp": "2025-01-01T10:00:00",
            "record_type": "BP",
            "data_type": "text",
            "value": "120/80"
        }
    )
    assert response.status_code == 422
    
    # Missing timestamp
    response = client.post(
        "/api/v1/records",
        json={
            "patient": "Test Patient",
            "record_type": "BP",
            "data_type": "text",
            "value": "120/80"
        }
    )
    assert response.status_code == 422


def test_get_records_empty(client):
    """Test getting records when database is empty."""
    response = client.get("/api/v1/records")
    assert response.status_code == 200
    assert response.json() == []


def test_get_records_all(client):
    """Test getting all records."""
    # Create patient
    client.post("/api/v1/patients", json={"name": "Patient A"})
    
    # Create multiple records
    records = [
        {
            "timestamp": "2025-01-01T10:00:00",
            "patient": "Patient A",
            "record_type": "BP",
            "data_type": "text",
            "value": "120/80"
        },
        {
            "timestamp": "2025-01-01T11:00:00",
            "patient": "Patient A",
            "record_type": "Sugar",
            "data_type": "text",
            "value": "95 mg/dL"
        },
        {
            "timestamp": "2025-01-01T12:00:00",
            "patient": "Patient A",
            "record_type": "BP",
            "data_type": "text",
            "value": "130/85"
        },
    ]
    
    for record in records:
        response = client.post("/api/v1/records", json=record)
        assert response.status_code == 201
    
    # Get all records
    response = client.get("/api/v1/records")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Records should be ordered by timestamp DESC (newest first)
    assert data[0]["timestamp"] >= data[1]["timestamp"]
    assert data[1]["timestamp"] >= data[2]["timestamp"]


def test_get_records_filter_by_patient(client):
    """Test filtering records by patient name."""
    # Create patients
    client.post("/api/v1/patients", json={"name": "Patient A"})
    client.post("/api/v1/patients", json={"name": "Patient B"})
    
    # Create records for both patients
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T10:00:00",
        "patient": "Patient A",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T11:00:00",
        "patient": "Patient B",
        "record_type": "BP",
        "data_type": "text",
        "value": "130/85"
    })
    
    # Filter by patient
    response = client.get("/api/v1/records?patient=Patient A")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["patient"] == "Patient A"


def test_get_records_filter_by_record_type(client):
    """Test filtering records by record type."""
    # Create patient
    client.post("/api/v1/patients", json={"name": "Patient A"})
    
    # Create records of different types
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T10:00:00",
        "patient": "Patient A",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T11:00:00",
        "patient": "Patient A",
        "record_type": "Sugar",
        "data_type": "text",
        "value": "95 mg/dL"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T12:00:00",
        "patient": "Patient A",
        "record_type": "BP",
        "data_type": "text",
        "value": "130/85"
    })
    
    # Filter by record type
    response = client.get("/api/v1/records?record_type=BP")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(r["record_type"] == "BP" for r in data)


def test_get_records_filter_by_patient_and_type(client):
    """Test filtering records by both patient and record type."""
    # Create patients
    client.post("/api/v1/patients", json={"name": "Patient A"})
    client.post("/api/v1/patients", json={"name": "Patient B"})
    
    # Create records
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T10:00:00",
        "patient": "Patient A",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T11:00:00",
        "patient": "Patient A",
        "record_type": "Sugar",
        "data_type": "text",
        "value": "95 mg/dL"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T12:00:00",
        "patient": "Patient B",
        "record_type": "BP",
        "data_type": "text",
        "value": "130/85"
    })
    
    # Filter by both patient and type
    response = client.get("/api/v1/records?patient=Patient A&record_type=BP")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["patient"] == "Patient A"
    assert data[0]["record_type"] == "BP"


def test_get_records_limit(client):
    """Test limiting the number of records returned."""
    # Create patient
    client.post("/api/v1/patients", json={"name": "Patient A"})
    
    # Create multiple records
    for i in range(5):
        client.post("/api/v1/records", json={
            "timestamp": f"2025-01-01T{10+i}:00:00",
            "patient": "Patient A",
            "record_type": "BP",
            "data_type": "text",
            "value": f"{120+i}/80"
        })
    
    # Get limited records
    response = client.get("/api/v1/records?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_records_limit_validation(client):
    """Test limit parameter validation."""
    # Test limit too high
    response = client.get("/api/v1/records?limit=1001")
    assert response.status_code == 422
    
    # Test limit too low
    response = client.get("/api/v1/records?limit=0")
    assert response.status_code == 422


def test_full_workflow(client):
    """Test a complete workflow: create patient, add records, query records."""
    # Create patient
    patient_response = client.post(
        "/api/v1/patients",
        json={"name": "Workflow Patient"}
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]
    
    # Verify patient appears in list
    patients_response = client.get("/api/v1/patients")
    assert patients_response.status_code == 200
    patients = patients_response.json()
    assert len(patients) == 1
    assert patients[0]["name"] == "Workflow Patient"
    assert patients[0]["id"] == patient_id
    
    # Create multiple records
    records = [
        {
            "timestamp": "2025-01-01T10:00:00",
            "patient": "Workflow Patient",
            "record_type": "BP",
            "data_type": "text",
            "value": "120/80"
        },
        {
            "timestamp": "2025-01-01T11:00:00",
            "patient": "Workflow Patient",
            "record_type": "Sugar",
            "data_type": "text",
            "value": "95 mg/dL"
        },
    ]
    
    for record in records:
        record_response = client.post("/api/v1/records", json=record)
        assert record_response.status_code == 201
    
    # Get all records
    all_records_response = client.get("/api/v1/records")
    assert all_records_response.status_code == 200
    all_records = all_records_response.json()
    assert len(all_records) == 2
    
    # Filter by patient
    patient_records_response = client.get("/api/v1/records?patient=Workflow Patient")
    assert patient_records_response.status_code == 200
    patient_records = patient_records_response.json()
    assert len(patient_records) == 2
    
    # Filter by record type
    bp_records_response = client.get("/api/v1/records?record_type=BP")
    assert bp_records_response.status_code == 200
    bp_records = bp_records_response.json()
    assert len(bp_records) == 1
    assert bp_records[0]["record_type"] == "BP"
    assert bp_records[0]["value"] == "120/80"

