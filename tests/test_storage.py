"""
Unit tests for storage/database layer.
Tests save_record and get_records functionality for SQLite backend.
"""
import os
import tempfile
import pytest
from datetime import datetime

from storage.database import Database
from storage.models import HealthRecord


# Sample test data
SAMPLE_RECORDS = [
    {
        "timestamp": datetime(2024, 1, 15, 10, 30, 0),
        "patient": "Nazra Mastoor",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    },
    {
        "timestamp": datetime(2024, 1, 15, 11, 0, 0),
        "patient": "Nazra Mastoor",
        "record_type": "Sugar",
        "data_type": "text",
        "value": "95 mg/dL"
    },
    {
        "timestamp": datetime(2024, 1, 15, 10, 45, 0),
        "patient": "Asgar Ali Ansari",
        "record_type": "BP",
        "data_type": "text",
        "value": "130/85"
    },
    {
        "timestamp": datetime(2024, 1, 16, 9, 0, 0),
        "patient": "Asgar Ali Ansari",
        "record_type": "Weight",
        "data_type": "text",
        "value": "75 kg"
    },
]


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


def test_save_record_basic(temp_db):
    """Test basic save_record functionality."""
    record_data = SAMPLE_RECORDS[0]
    
    record_id = temp_db.save_record(
        timestamp=record_data["timestamp"],
        patient=record_data["patient"],
        record_type=record_data["record_type"],
        data_type=record_data["data_type"],
        value=record_data["value"]
    )
    
    assert record_id == 1, "First record should have ID 1"


def test_save_record_returns_incremental_ids(temp_db):
    """Test that save_record returns incremental IDs."""
    record_ids = []
    
    for record_data in SAMPLE_RECORDS:
        record_id = temp_db.save_record(
            timestamp=record_data["timestamp"],
            patient=record_data["patient"],
            record_type=record_data["record_type"],
            data_type=record_data["data_type"],
            value=record_data["value"]
        )
        record_ids.append(record_id)
    
    assert record_ids == [1, 2, 3, 4], "IDs should be incremental"


def test_get_records_all(temp_db):
    """Test get_records without filters returns all records."""
    # Save all sample records
    for record_data in SAMPLE_RECORDS:
        temp_db.save_record(**record_data)
    
    records = temp_db.get_records()
    
    assert len(records) == 4, "Should return all 4 records"
    assert all(isinstance(r, HealthRecord) for r in records), "All should be HealthRecord objects"


def test_get_records_filter_by_patient(temp_db):
    """Test get_records with patient filter."""
    # Save all sample records
    for record_data in SAMPLE_RECORDS:
        temp_db.save_record(**record_data)
    
    # Filter by patient
    records = temp_db.get_records(patient="Nazra Mastoor")
    
    assert len(records) == 2, "Should return 2 records for Nazra Mastoor"
    assert all(r.patient == "Nazra Mastoor" for r in records), "All records should be for Nazra Mastoor"


def test_get_records_filter_by_type(temp_db):
    """Test get_records with record_type filter."""
    # Save all sample records
    for record_data in SAMPLE_RECORDS:
        temp_db.save_record(**record_data)
    
    # Filter by record type
    records = temp_db.get_records(record_type="BP")
    
    assert len(records) == 2, "Should return 2 BP records"
    assert all(r.record_type == "BP" for r in records), "All records should be BP type"


def test_get_records_filter_by_patient_and_type(temp_db):
    """Test get_records with both patient and record_type filters."""
    # Save all sample records
    for record_data in SAMPLE_RECORDS:
        temp_db.save_record(**record_data)
    
    # Filter by patient and type
    records = temp_db.get_records(patient="Asgar Ali Ansari", record_type="BP")
    
    assert len(records) == 1, "Should return 1 record"
    assert records[0].patient == "Asgar Ali Ansari", "Patient should match"
    assert records[0].record_type == "BP", "Record type should match"


def test_get_records_limit(temp_db):
    """Test get_records with limit parameter."""
    # Save all sample records
    for record_data in SAMPLE_RECORDS:
        temp_db.save_record(**record_data)
    
    # Get limited records (should be ordered by timestamp DESC)
    records = temp_db.get_records(limit=2)
    
    assert len(records) == 2, "Should return only 2 records"
    # Verify they are ordered by timestamp DESC (newest first)
    assert records[0].timestamp >= records[1].timestamp, "Should be ordered DESC"


def test_get_records_ordering(temp_db):
    """Test that get_records returns records in descending timestamp order."""
    # Save records with different timestamps
    for record_data in SAMPLE_RECORDS:
        temp_db.save_record(**record_data)
    
    records = temp_db.get_records()
    
    # Verify descending order
    for i in range(len(records) - 1):
        assert records[i].timestamp >= records[i + 1].timestamp, \
            "Records should be ordered by timestamp DESC"


def test_get_records_empty_database(temp_db):
    """Test get_records on empty database returns empty list."""
    records = temp_db.get_records()
    
    assert records == [], "Should return empty list for empty database"


def test_save_and_retrieve_record_data_integrity(temp_db):
    """Test that saved data is correctly retrieved."""
    record_data = SAMPLE_RECORDS[0]
    
    # Save record
    temp_db.save_record(**record_data)
    
    # Retrieve records
    records = temp_db.get_records()
    
    assert len(records) == 1, "Should have one record"
    retrieved = records[0]
    
    # Compare all fields
    assert retrieved.timestamp == record_data["timestamp"], "Timestamp should match"
    assert retrieved.patient == record_data["patient"], "Patient should match"
    assert retrieved.record_type == record_data["record_type"], "Record type should match"
    assert retrieved.data_type == record_data["data_type"], "Data type should match"
    assert retrieved.value == record_data["value"], "Value should match"


def test_multiple_saves_and_retrievals(temp_db):
    """Test multiple save and retrieval operations."""
    # Save records one by one and verify
    for i, record_data in enumerate(SAMPLE_RECORDS, 1):
        temp_db.save_record(**record_data)
        
        records = temp_db.get_records()
        assert len(records) == i, f"Should have {i} records after {i} saves"

