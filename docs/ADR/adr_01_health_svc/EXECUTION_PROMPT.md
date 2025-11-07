# Execution Prompt: Health Service Refactoring

Use this prompt to guide the implementation of the health service refactoring as documented in the ADR.

---

## Prompt for AI Assistant

I need you to implement the refactoring plan documented in `docs/ADR/adr_01_health_svc/`. Please follow the step-by-step instructions below:

### Context
- Current codebase: Health Bot with Telegram bot that directly accesses SQLite database
- Goal: Extract all database logic into a new `health_svc` service with FastAPI REST API
- Reference documents:
  - `docs/ADR/adr_01_health_svc/REFACTORING_PLAN.md` - Complete refactoring plan
  - `docs/ADR/adr_01_health_svc/IMPLEMENTATION_GUIDE.md` - Detailed code examples
  - `docs/ADR/adr_01_health_svc/MIGRATION_CHECKLIST.md` - Step-by-step checklist
  - `docs/ADR/adr_01_health_svc/REFACTORING_SUMMARY.md` - Quick reference guide

### Phase 1: Create Health Service Structure

1. Create the `health_svc/` folder structure:
   ```
   health_svc/
   ├── __init__.py
   ├── main.py
   ├── config.py
   ├── api/
   │   ├── __init__.py
   │   ├── routes.py
   │   └── schemas.py
   ├── services/
   │   ├── __init__.py
   │   ├── health_service.py
   │   └── patient_service.py
   ├── storage/
   │   ├── __init__.py
   │   ├── database.py
   │   └── models.py
   └── requirements.txt
   ```

2. Move database code:
   - Copy `telegram_bot/storage/database.py` → `health_svc/storage/database.py`
   - Copy `telegram_bot/storage/models.py` → `health_svc/storage/models.py`
   - Update imports in moved files to use relative imports or `health_svc.config`

3. Create `health_svc/config.py` with:
   - Database configuration (DATABASE_DIR, DATABASE_FILE, DATABASE_PATH)
   - API configuration (API_HOST, API_PORT, API_RELOAD)
   - Use environment variables with HEALTH_SVC_ prefix

### Phase 2: Implement FastAPI Service

1. Create Pydantic schemas in `health_svc/api/schemas.py`:
   - `PatientCreate` - for creating patients
   - `PatientResponse` - for patient responses
   - `HealthRecordCreate` - for creating records
   - `HealthRecordResponse` - for record responses

2. Create service layer:
   - `health_svc/services/health_service.py` - wraps database operations for health records
   - `health_svc/services/patient_service.py` - wraps database operations for patients
   - Both should use the Database class from storage layer

3. Create FastAPI routes in `health_svc/api/routes.py`:
   - `GET /` - root endpoint
   - `GET /api/v1/patients` - list all patients
   - `POST /api/v1/patients` - create new patient
   - `GET /api/v1/records` - get records (with query params: patient, record_type, limit)
   - `POST /api/v1/records` - create new record

4. Create FastAPI app in `health_svc/main.py`:
   - Initialize FastAPI with CORS middleware
   - Include router from api/routes
   - Add startup event to initialize database
   - Configure uvicorn to run the app

5. Create `health_svc/requirements.txt`:
   - fastapi>=0.104.0
   - uvicorn[standard]>=0.24.0
   - pydantic>=2.0.0

### Phase 3: Create HTTP Client for Telegram Bot

1. Create `telegram_bot/clients/` directory with:
   - `__init__.py`
   - `health_api_client.py` - HTTP client class

2. Implement `HealthAPIClient` class with:
   - `_request()` helper method for HTTP calls
   - `add_patient(name)` - async method
   - `get_patients()` - async method
   - `save_record(...)` - async method
   - `get_records(...)` - async method
   - Proper error handling (ConnectionError, ValueError)

3. Update `telegram_bot/config.py`:
   - Remove database configuration (DATABASE_DIR, DATABASE_PATH)
   - Add `HEALTH_SVC_API_URL` configuration
   - Update `load_env()` documentation

4. Update `telegram_bot/requirements.txt`:
   - Add `httpx>=0.25.0`

### Phase 4: Update Telegram Bot Handlers

Update all handler files to use HTTP client instead of direct database access:

1. `telegram_bot/handlers/add_record.py`:
   - Replace `from storage.database import get_database` with `from clients.health_api_client import get_health_api_client`
   - Update all `get_database()` calls to `get_health_api_client()`
   - Make all API calls async with `await`
   - Update error handling for connection errors

2. `telegram_bot/handlers/add_patient.py`:
   - Same pattern as above
   - Handle ValueError for duplicate patients

3. `telegram_bot/handlers/get_patients.py`:
   - Replace database calls with HTTP client calls

4. `telegram_bot/handlers/view.py`:
   - Replace database calls with HTTP client calls
   - Parse timestamp strings from API responses (use `datetime.fromisoformat()`)

5. `telegram_bot/handlers/export.py`:
   - Replace database calls with HTTP client calls
   - Parse timestamp strings from API responses

### Phase 5: Testing & Cleanup

1. Test the Health Service API:
   - Start the API server
   - Test all endpoints with curl or Postman
   - Verify database operations work correctly

2. Test the Telegram Bot:
   - Start the bot
   - Test all commands end-to-end
   - Verify error handling works

3. Cleanup:
   - Remove `telegram_bot/storage/` directory (after confirming everything works)
   - Update any remaining imports
   - Run all existing tests and update as needed

### Important Notes

- Maintain backwards compatibility - no changes to database schema
- All business logic remains unchanged, only location changes
- Use async/await for all HTTP client calls
- Handle errors gracefully with user-friendly messages
- Follow the exact code patterns from IMPLEMENTATION_GUIDE.md
- Check off items in MIGRATION_CHECKLIST.md as you complete them

### Expected Outcome

After implementation:
- `health_svc/` folder with complete FastAPI service
- `telegram_bot/clients/health_api_client.py` with HTTP client
- All handlers updated to use HTTP client
- Both services can run independently
- All existing functionality preserved

Please implement this refactoring step by step, following the documentation in `docs/ADR/adr_01_health_svc/`. Start with Phase 1 and proceed sequentially. Ask for clarification if any step is unclear.

---

## Alternative: Step-by-Step Execution

If you prefer to implement incrementally, use these prompts for each phase:

### Phase 1 Prompt
```
Implement Phase 1 of the health service refactoring:
1. Create the health_svc/ folder structure
2. Move database code from telegram_bot/storage/ to health_svc/storage/
3. Create health_svc/config.py with proper configuration

Reference: docs/ADR/adr_01_health_svc/REFACTORING_PLAN.md section 3.1
```

### Phase 2 Prompt
```
Implement Phase 2 of the health service refactoring:
1. Create Pydantic schemas in health_svc/api/schemas.py
2. Create service layer (health_service.py and patient_service.py)
3. Create FastAPI routes in health_svc/api/routes.py
4. Create FastAPI app in health_svc/main.py
5. Create requirements.txt

Reference: docs/ADR/adr_01_health_svc/IMPLEMENTATION_GUIDE.md Part 1
```

### Phase 3 Prompt
```
Implement Phase 3 of the health service refactoring:
1. Create telegram_bot/clients/health_api_client.py
2. Update telegram_bot/config.py
3. Update telegram_bot/requirements.txt

Reference: docs/ADR/adr_01_health_svc/IMPLEMENTATION_GUIDE.md Part 2
```

### Phase 4 Prompt
```
Implement Phase 4 of the health service refactoring:
Update all handler files to use HTTP client:
- handlers/add_record.py
- handlers/add_patient.py
- handlers/get_patients.py
- handlers/view.py
- handlers/export.py

Reference: docs/ADR/adr_01_health_svc/IMPLEMENTATION_GUIDE.md Part 3
```

### Phase 5 Prompt
```
Complete Phase 5 of the health service refactoring:
1. Test Health Service API
2. Test Telegram Bot
3. Remove old storage/ directory
4. Update tests

Reference: docs/ADR/adr_01_health_svc/MIGRATION_CHECKLIST.md Phase 5
```

---

## Quick Start Command

To execute the full refactoring, use this prompt:

```
I need to implement the health service refactoring as documented in docs/ADR/adr_01_health_svc/. 

Please:
1. Read all the documentation files in that directory
2. Follow the step-by-step implementation guide
3. Create all necessary files and folders
4. Update all handler files to use the HTTP client
5. Ensure backwards compatibility is maintained
6. Test each phase before moving to the next

Start with Phase 1 and proceed sequentially through all 5 phases.
```

---

## Verification Checklist

After implementation, verify:
- [ ] `health_svc/` folder exists with all required files
- [ ] `telegram_bot/clients/health_api_client.py` exists
- [ ] All handlers updated to use HTTP client
- [ ] `telegram_bot/config.py` updated (no DB config, has API URL)
- [ ] `telegram_bot/storage/` removed (or ready to be removed)
- [ ] Both services can start independently
- [ ] All bot commands work as before
- [ ] Error handling works correctly

