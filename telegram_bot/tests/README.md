# Running Tests

## Installation

First, install the test dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support

## Running Tests

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

### Run with Detailed Output
```bash
pytest tests/ -vv
```

### Run Specific Test
```bash
pytest tests/test_storage.py::test_save_record_basic
pytest tests/test_add_record_handler.py::test_value_received_saves_record
```

### Run with Coverage Report
```bash
pytest tests/ --cov=storage --cov=handlers --cov-report=html
```

This generates an HTML coverage report in `htmlcov/` directory.

## Test Structure

### Storage Tests (`test_storage.py`)
- Tests database save/retrieve operations
- Uses temporary databases (isolated per test)
- Tests filtering, ordering, and data integrity

### Handler Tests (`test_add_record_handler.py`)
- Tests add_record handler flow
- Mocks Telegram Update/Context objects
- Tests record persistence through handler
- Includes manual integration test instructions

## Expected Output

All tests should pass:
```
======================== test session starts ========================
platform darwin -- Python 3.x.x, pytest-x.x.x, pluggy-x.x.x
collected 16 items

tests/test_add_record_handler.py .........                    [ 56%]
tests/test_storage.py ........                                 [100%]

======================= 16 passed in X.XXs ========================
```

## Manual Integration Testing

For end-to-end testing with the actual Telegram bot:

1. Start the bot:
   ```bash
   python bot.py
   ```

2. In Telegram:
   - Send `/start` to initialize
   - Send `/add_record`
   - Select a patient from inline buttons
   - Select a record type from inline buttons
   - Enter a value (e.g., "120/80" for BP)

3. Verify in database:
   - Check `data/health_bot.db` using SQLite tools
   - Or use `/view_records` to see the saved entry

4. Expected behavior:
   - Record is saved with correct patient, type, and value
   - Confirmation message shows all record details
   - Record appears in `/view_records` output

