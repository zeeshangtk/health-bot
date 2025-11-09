"""
Tests for health record endpoints.
"""
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
        "value": "120/80",
        "unit": "mmHg"
    }
    response = client.post("/api/v1/records", json=record_data)
    assert response.status_code == 201
    data = response.json()
    assert data["patient"] == "Test Patient"
    assert data["record_type"] == "BP"
    assert data["value"] == "120/80"
    assert data["unit"] == "mmHg"
    assert data["lab_name"] == "self", "lab_name should default to 'self'"
    assert "timestamp" in data


def test_create_record_patient_not_found(client):
    """Test creating a record for non-existent patient returns 400."""
    record_data = {
        "timestamp": "2025-01-01T10:00:00",
        "patient": "Non-existent Patient",
        "record_type": "BP",
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
            "value": "120/80",
            "unit": "mmHg"
        },
        {
            "timestamp": "2025-01-01T11:00:00",
            "patient": "Patient A",
            "record_type": "Sugar",
            "value": "95",
            "unit": "mg/dL"
        },
        {
            "timestamp": "2025-01-01T12:00:00",
            "patient": "Patient A",
            "record_type": "BP",
            "value": "130/85",
            "unit": "mmHg"
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
        "value": "120/80"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T11:00:00",
        "patient": "Patient B",
        "record_type": "BP",
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
        "value": "120/80"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T11:00:00",
        "patient": "Patient A",
        "record_type": "Sugar",
        "value": "95",
        "unit": "mg/dL"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T12:00:00",
        "patient": "Patient A",
        "record_type": "BP",
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
        "value": "120/80"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T11:00:00",
        "patient": "Patient A",
        "record_type": "Sugar",
        "value": "95",
        "unit": "mg/dL"
    })
    client.post("/api/v1/records", json={
        "timestamp": "2025-01-01T12:00:00",
        "patient": "Patient B",
        "record_type": "BP",
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
            "value": "120/80",
            "unit": "mmHg"
        },
        {
            "timestamp": "2025-01-01T11:00:00",
            "patient": "Workflow Patient",
            "record_type": "Sugar",
            "value": "95",
            "unit": "mg/dL",
            "lab_name": "City Lab"
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

