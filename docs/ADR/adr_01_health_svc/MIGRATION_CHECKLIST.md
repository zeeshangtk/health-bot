# Migration Checklist

Use this checklist to track progress during the refactoring.

## Phase 1: Create Health Service Structure

### Folder Structure
- [ ] Create `health_svc/` directory
- [ ] Create `health_svc/api/` directory
- [ ] Create `health_svc/services/` directory
- [ ] Create `health_svc/storage/` directory
- [ ] Create `health_svc/models/` directory (if needed)
- [ ] Create all `__init__.py` files

### Configuration
- [ ] Create `health_svc/config.py`
- [ ] Add database path configuration
- [ ] Add API server configuration (host, port, reload)

### Move Database Code
- [ ] Copy `telegram_bot/storage/database.py` → `health_svc/storage/database.py`
- [ ] Copy `telegram_bot/storage/models.py` → `health_svc/storage/models.py`
- [ ] Update imports in `health_svc/storage/database.py`
- [ ] Update imports in `health_svc/storage/models.py`
- [ ] Test database initialization works

---

## Phase 2: Implement FastAPI Service

### Pydantic Schemas
- [ ] Create `health_svc/api/schemas.py`
- [ ] Define `PatientCreate` schema
- [ ] Define `PatientResponse` schema
- [ ] Define `HealthRecordCreate` schema
- [ ] Define `HealthRecordResponse` schema
- [ ] Add field validations
- [ ] Add example values

### Service Layer
- [ ] Create `health_svc/services/health_service.py`
- [ ] Implement `HealthService.save_record()` method
- [ ] Implement `HealthService.get_records()` method
- [ ] Add error handling in service methods
- [ ] Create `health_svc/services/patient_service.py`
- [ ] Implement `PatientService.add_patient()` method
- [ ] Implement `PatientService.get_patients()` method
- [ ] Add error handling in service methods

### FastAPI Routes
- [ ] Create `health_svc/api/routes.py`
- [ ] Implement `GET /` root endpoint
- [ ] Implement `GET /api/v1/patients` endpoint
- [ ] Implement `POST /api/v1/patients` endpoint
- [ ] Implement `GET /api/v1/records` endpoint (with query params)
- [ ] Implement `POST /api/v1/records` endpoint
- [ ] Add proper HTTP status codes
- [ ] Add error handling (HTTPException)

### FastAPI Application
- [ ] Create `health_svc/main.py`
- [ ] Initialize FastAPI app
- [ ] Add CORS middleware
- [ ] Include router
- [ ] Add startup event for DB initialization
- [ ] Add uvicorn run configuration

### Requirements
- [ ] Create `health_svc/requirements.txt`
- [ ] Add `fastapi>=0.104.0`
- [ ] Add `uvicorn[standard]>=0.24.0`
- [ ] Add `pydantic>=2.0.0`

### Testing API
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start API server: `python main.py`
- [ ] Test `GET /` endpoint
- [ ] Test `GET /api/v1/patients` (should return empty list initially)
- [ ] Test `POST /api/v1/patients` (create a patient)
- [ ] Test `GET /api/v1/patients` (verify patient appears)
- [ ] Test `POST /api/v1/records` (create a record)
- [ ] Test `GET /api/v1/records` (verify record appears)
- [ ] Test query parameters (patient filter, record_type filter, limit)
- [ ] Test error cases (duplicate patient, invalid data)

---

## Phase 3: Create HTTP Client for Telegram Bot

### Client Module
- [ ] Create `telegram_bot/clients/` directory
- [ ] Create `telegram_bot/clients/__init__.py`
- [ ] Create `telegram_bot/clients/health_api_client.py`
- [ ] Implement `HealthAPIClient` class
- [ ] Implement `_request()` helper method
- [ ] Implement `add_patient()` method
- [ ] Implement `get_patients()` method
- [ ] Implement `save_record()` method
- [ ] Implement `get_records()` method
- [ ] Add error handling (ConnectionError, ValueError)
- [ ] Add logging
- [ ] Implement `get_health_api_client()` function

### Update Configuration
- [ ] Update `telegram_bot/config.py`
- [ ] Remove database configuration (DATABASE_DIR, DATABASE_PATH)
- [ ] Add `HEALTH_SVC_API_URL` configuration
- [ ] Update `load_env()` function documentation

### Update Requirements
- [ ] Update `telegram_bot/requirements.txt`
- [ ] Add `httpx>=0.25.0`

### Testing Client
- [ ] Ensure Health Service API is running
- [ ] Test client initialization
- [ ] Test `client.get_patients()` (async)
- [ ] Test `client.add_patient()` (async)
- [ ] Test `client.save_record()` (async)
- [ ] Test `client.get_records()` (async)
- [ ] Test error handling (connection errors, API errors)

---

## Phase 4: Update Telegram Bot Handlers

### Handler: add_record.py
- [ ] Replace `from storage.database import get_database`
- [ ] Add `from clients.health_api_client import get_health_api_client`
- [ ] Update `add_record_command()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
  - [ ] Add error handling for connection errors
- [ ] Update `patient_selected()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
- [ ] Update `value_received()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `save_record()` call async with `await`
  - [ ] Update response handling (dict instead of object)
  - [ ] Add error handling

### Handler: add_patient.py
- [ ] Replace `from storage.database import get_database`
- [ ] Add `from clients.health_api_client import get_health_api_client`
- [ ] Update `process_patient_name()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `add_patient()` call async with `await`
  - [ ] Update error handling (catch ValueError for duplicate)
  - [ ] Add connection error handling

### Handler: get_patients.py
- [ ] Replace `from storage.database import get_database`
- [ ] Add `from clients.health_api_client import get_health_api_client`
- [ ] Update `get_patients_command()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
  - [ ] Add connection error handling

### Handler: view.py
- [ ] Replace `from storage.database import get_database`
- [ ] Add `from clients.health_api_client import get_health_api_client`
- [ ] Update `view_records_command()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
- [ ] Update `patient_selected_for_view()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
- [ ] Update `record_type_selected_for_view()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_records()` call async with `await`
  - [ ] Update record parsing (timestamp from ISO string)
  - [ ] Add connection error handling

### Handler: export.py
- [ ] Replace `from storage.database import get_database`
- [ ] Add `from clients.health_api_client import get_health_api_client`
- [ ] Update `export_command()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
- [ ] Update `patient_selected_for_export()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_patients()` call async with `await`
- [ ] Update `format_selected_for_export()` function
  - [ ] Replace `get_database()` with `get_health_api_client()`
  - [ ] Make `get_records()` call async with `await`
  - [ ] Update record parsing (timestamp from ISO string)
  - [ ] Add connection error handling

### Testing Handlers
- [ ] Test `/add_patient` command
- [ ] Test `/get_patients` command
- [ ] Test `/add_record` command (full flow)
- [ ] Test `/view_records` command (full flow)
- [ ] Test `/export` command (full flow)
- [ ] Test error scenarios (API down, invalid data)

---

## Phase 5: Cleanup & Finalization

### Remove Old Code
- [ ] Remove `telegram_bot/storage/` directory
- [ ] Verify no remaining imports of `storage.database`
- [ ] Search codebase for any remaining `get_database()` calls

### Update Tests
- [ ] Move database tests to `health_svc/tests/`
- [ ] Create API integration tests
- [ ] Update telegram bot tests to mock HTTP client
- [ ] Run all tests and verify they pass

### Documentation
- [ ] Update `health_svc/README.md` with setup instructions
- [ ] Update `telegram_bot/README.md` with new setup instructions
- [ ] Create `.env.example` for health_svc service
- [ ] Create `.env.example` for telegram_bot
- [ ] Document environment variables
- [ ] Document API endpoints

### Environment Setup
- [ ] Create `.env.example` files
- [ ] Document required environment variables
- [ ] Test with environment variables set

### Final Testing
- [ ] Start Health Service API
- [ ] Start Telegram Bot
- [ ] Test all bot commands end-to-end
- [ ] Verify database operations work correctly
- [ ] Test error handling (stop API, verify bot handles gracefully)
- [ ] Test with multiple concurrent requests

### Deployment Preparation
- [ ] Document how to run both services
- [ ] Document production configuration
- [ ] Consider Docker setup (optional)
- [ ] Consider process management (systemd, supervisor, etc.)

---

## Verification Checklist

### Functionality
- [ ] All bot commands work as before
- [ ] Database operations unchanged
- [ ] Data integrity maintained
- [ ] Error messages user-friendly

### Code Quality
- [ ] No linting errors
- [ ] All imports correct
- [ ] No unused code
- [ ] Proper error handling everywhere

### Documentation
- [ ] README files updated
- [ ] Code comments updated
- [ ] API documentation clear
- [ ] Environment variables documented

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing complete
- [ ] Error scenarios tested

---

## Rollback Plan (If Needed)

If issues arise, rollback steps:
1. Stop both services
2. Restore `telegram_bot/storage/` from backup
3. Revert handler changes (use git)
4. Revert config changes
5. Restart telegram bot with old code

---

## Notes

- Test each phase before moving to the next
- Keep backups of original code
- Use version control (git) for easy rollback
- Test in development environment first
- Document any issues encountered

---

## Completion

- [ ] All phases complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Ready for production deployment

**Date Completed**: _______________
**Completed By**: _______________

