# Test Plan for Health Bot

## Overview
This test plan covers unit testing for the storage layer and add_record handler flow.

## Test Categories

### 1. Storage Layer Tests (`tests/test_storage.py`)
Tests for `Database.save_record()` and `Database.get_records()` methods.

**Test Cases:**
- ✅ Basic save_record functionality
- ✅ Incremental ID generation
- ✅ Get all records without filters
- ✅ Filter by patient
- ✅ Filter by record type
- ✅ Filter by both patient and record type
- ✅ Limit parameter
- ✅ Records ordered by timestamp DESC
- ✅ Empty database handling
- ✅ Data integrity (save and retrieve)
- ✅ Multiple saves and retrievals

**Test Data:**
- 4 sample records with different patients, types, and timestamps
- Covers: BP, Sugar, Weight record types
- Covers: Multiple patients

### 2. Add Record Handler Tests (`tests/test_add_record_handler.py`)
Tests for the `value_received` handler function to ensure records are persisted.

**Test Cases:**
- ✅ Handler saves record to database
- ✅ Handler handles missing context gracefully
- ✅ Handler rejects empty/whitespace values
- ✅ Handler can save multiple records
- ✅ Timestamp is correctly set

**Mocking:**
- Telegram Update object
- Telegram Context object
- Database instance (using temp database)

**Manual Integration Test:**
- Instructions provided for manual end-to-end testing

## Test Execution

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_storage.py
pytest tests/test_add_record_handler.py
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=storage --cov=handlers
```

## Test Isolation

- Each test uses a temporary SQLite database
- Databases are created per test and cleaned up afterward
- No interference between tests
- No modification of production database

## Sample Test Data

**Records Used:**
1. Nazra Mastoor - BP - "120/80" - 2024-01-15 10:30
2. Nazra Mastoor - Sugar - "95 mg/dL" - 2024-01-15 11:00
3. Asgar Ali Ansari - BP - "130/85" - 2024-01-15 10:45
4. Asgar Ali Ansari - Weight - "75 kg" - 2024-01-16 09:00

## Future Test Additions

- [ ] View records handler tests
- [ ] Export handler tests
- [ ] Error handling edge cases
- [ ] Database connection error handling
- [ ] Concurrent access tests

