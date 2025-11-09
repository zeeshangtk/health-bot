"""
Tests for patient endpoints.
"""
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

