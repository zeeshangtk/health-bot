# Running Tests

## Installation

First, install the test dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `httpx` - HTTP client library (for API client tests)

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_storage.py
pytest tests/test_add_record_handler.py
pytest tests/test_health_api_client.py
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Detailed Output
```bash
pytest tests/ -vv
```

### Run Specific Test
```bash
pytest tests/test_storage.py::test_save_record_basic
pytest tests/test_add_record_handler.py::test_value_received_saves_record
pytest tests/test_health_api_client.py::test_get_patients_success
```

### Run with Coverage Report
```bash
pytest tests/ --cov=clients --cov=handlers --cov-report=html
```

This generates an HTML coverage report in `htmlcov/` directory.

## Test Structure

### Storage Tests (`test_storage.py`)
- Tests database save/retrieve operations directly
- Uses temporary databases (isolated per test)
- Tests filtering, ordering, and data integrity
- **Note**: These tests will be moved to `health_svc/tests/` after refactoring

### HTTP Client Tests (`test_health_api_client.py`)
- Tests the HealthAPIClient class
- Mocks HTTP requests/responses
- Tests all API methods (get_patients, add_patient, save_record, get_records)
- Tests error handling (connection errors, HTTP errors)

### Handler Tests (`test_add_record_handler.py`)
- Tests add_record handler flow
- Mocks Telegram Update/Context objects
- Mocks HealthAPIClient instead of direct database access
- Tests record persistence through API client
- Tests error handling for API failures
- Includes manual integration test instructions

## Expected Output

All tests should pass:
```
======================== test session starts ========================
platform darwin -- Python 3.x.x, pytest-x.x.x, pluggy-x.x.x
collected XX items

tests/test_add_record_handler.py .........                    [ XX%]
tests/test_health_api_client.py ..........                  [ XX%]
tests/test_storage.py ........                                 [ XX%]

======================= XX passed in X.XXs ========================
```

## Manual Integration Testing

For end-to-end testing with the actual Telegram bot and Health Service API:

1. Start the Health Service API:
   ```bash
   cd health_svc
   python main.py
   ```
   The API should be running on `http://localhost:8000`

2. Start the bot:
   ```bash
   cd telegram_bot
   export HEALTH_SVC_API_URL=http://localhost:8000
   python bot.py
   ```

3. In Telegram:
   - Send `/start` to initialize
   - Send `/add_record`
   - Select a patient from inline buttons
   - Select a record type from inline buttons
   - Enter a value (e.g., "120/80" for BP)

4. Verify via API:
   ```bash
   curl http://localhost:8000/api/v1/records
   ```
   Or use `/view_records` command in Telegram

5. Expected behavior:
   - Record is saved via API with correct patient, type, and value
   - Confirmation message shows all record details
   - Record appears in `/view_records` output
   - Record is accessible via API endpoints

## Testing Architecture

The tests follow the new architecture:
- **Handlers** → Mock `HealthAPIClient` → Test handler logic
- **HTTP Client** → Mock `httpx.AsyncClient` → Test API communication
- **Storage** → Direct database tests (will move to health_svc)

This separation allows testing each layer independently.

