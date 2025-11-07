# Refactoring Summary: Quick Reference

## Overview

**Goal**: Extract all database logic from `telegram_bot` into a new `health_svc` service with a FastAPI REST API.

**Key Changes**:
- Database code moves from `telegram_bot/storage/` → `health_svc/storage/`
- New FastAPI service in `health_svc/`
- Telegram bot uses HTTP client instead of direct DB access

---

## Before vs After Architecture

### Before
```
telegram_bot/
├── handlers/          → Direct DB calls via get_database()
├── storage/
│   ├── database.py   → SQLite operations
│   └── models.py     → Data models
└── bot.py
```

### After
```
telegram_bot/                    health_svc/
├── handlers/                    ├── api/
│   └── ... (use HTTP client)    │   ├── routes.py
├── clients/                      │   └── schemas.py
│   └── health_api_client.py     ├── services/
└── bot.py                        │   ├── health_service.py
                                  │   └── patient_service.py
                                  ├── storage/
                                  │   ├── database.py (moved)
                                  │   └── models.py (moved)
                                  └── main.py
```

---

## API Endpoints

### Health Service API (`http://localhost:8000`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/patients` | Get all patients |
| POST | `/api/v1/patients` | Create new patient |
| GET | `/api/v1/records` | Get records (with filters) |
| POST | `/api/v1/records` | Create new record |

**Query Parameters for GET `/api/v1/records`**:
- `patient` (optional): Filter by patient name
- `record_type` (optional): Filter by record type
- `limit` (optional): Limit results

---

## Code Pattern Changes

### Pattern 1: Getting Patients

**Before:**
```python
from storage.database import get_database

db = get_database()
patients = db.get_patients()
```

**After:**
```python
from clients.health_api_client import get_health_api_client

client = get_health_api_client()
patients = await client.get_patients()
```

### Pattern 2: Adding Patient

**Before:**
```python
db = get_database()
success = db.add_patient(name)
```

**After:**
```python
client = get_health_api_client()
try:
    result = await client.add_patient(name)
    success = True
except ValueError:
    success = False  # Patient already exists
```

### Pattern 3: Saving Record

**Before:**
```python
db = get_database()
record_id = db.save_record(
    timestamp=timestamp,
    patient=patient,
    record_type=record_type,
    data_type=data_type,
    value=value
)
```

**After:**
```python
client = get_health_api_client()
result = await client.save_record(
    timestamp=timestamp,
    patient=patient,
    record_type=record_type,
    data_type=data_type,
    value=value
)
# result is a dict with record data
```

### Pattern 4: Getting Records

**Before:**
```python
db = get_database()
records = db.get_records(patient=patient, record_type=type, limit=5)
# records is List[HealthRecord] objects
```

**After:**
```python
client = get_health_api_client()
records = await client.get_records(patient=patient, record_type=type, limit=5)
# records is List[dict] - need to parse timestamps
```

---

## Data Format Changes

### HealthRecord Object → Dict

**Before (HealthRecord object):**
```python
record.timestamp  # datetime object
record.patient    # str
record.record_type # str
record.data_type  # str
record.value      # str
```

**After (Dict from API):**
```python
from datetime import datetime

record["timestamp"]  # ISO string, parse with: datetime.fromisoformat(record["timestamp"])
record["patient"]    # str
record["record_type"] # str
record["data_type"]  # str
record["value"]      # str
```

### Patient Dict (Same Format)

Both return the same format:
```python
{
    "id": 1,
    "name": "John Doe",
    "created_at": "2025-01-01 10:00:00"
}
```

---

## Environment Variables

### Health Service
```bash
HEALTH_SVC_DB_DIR=data
HEALTH_SVC_DB_FILE=health_bot.db
HEALTH_SVC_HOST=0.0.0.0
HEALTH_SVC_PORT=8000
HEALTH_SVC_RELOAD=false
```

### Telegram Bot
```bash
TELEGRAM_TOKEN=your_token_here
HEALTH_SVC_API_URL=http://localhost:8000
```

---

## File Mapping

| Old Location | New Location | Notes |
|-------------|--------------|-------|
| `telegram_bot/storage/database.py` | `health_svc/storage/database.py` | Move & update imports |
| `telegram_bot/storage/models.py` | `health_svc/storage/models.py` | Move as-is |
| - | `health_svc/api/routes.py` | NEW: FastAPI routes |
| - | `health_svc/api/schemas.py` | NEW: Pydantic schemas |
| - | `health_svc/services/health_service.py` | NEW: Service layer |
| - | `health_svc/services/patient_service.py` | NEW: Service layer |
| - | `health_svc/main.py` | NEW: FastAPI app |
| - | `telegram_bot/clients/health_api_client.py` | NEW: HTTP client |
| `telegram_bot/config.py` | `telegram_bot/config.py` | UPDATE: Add API URL, remove DB config |
| `telegram_bot/handlers/*.py` | `telegram_bot/handlers/*.py` | UPDATE: Use HTTP client |

---

## Handler Files to Update

1. ✅ `handlers/add_record.py` - Replace `get_database()` with `get_health_api_client()`
2. ✅ `handlers/add_patient.py` - Replace `get_database()` with `get_health_api_client()`
3. ✅ `handlers/get_patients.py` - Replace `get_database()` with `get_health_api_client()`
4. ✅ `handlers/view.py` - Replace `get_database()` with `get_health_api_client()`
5. ✅ `handlers/export.py` - Replace `get_database()` with `get_health_api_client()`

---

## Error Handling

### Connection Errors
```python
try:
    patients = await client.get_patients()
except ConnectionError as e:
    logger.error(f"Connection error: {e}")
    await update.message.reply_text(
        "❌ Error connecting to health service. Please try again later."
    )
    return ConversationHandler.END
```

### Business Logic Errors
```python
try:
    result = await client.add_patient(name)
except ValueError as e:
    # Patient already exists or validation error
    await update.message.reply_text(f"❌ {str(e)}")
    return WAITING_FOR_NAME
```

---

## Testing Checklist

- [ ] Health Service API starts successfully
- [ ] API endpoints return correct responses
- [ ] Telegram bot connects to API
- [ ] All handlers work with HTTP client
- [ ] Error handling works correctly
- [ ] Database operations unchanged
- [ ] Existing tests updated/mocked

---

## Quick Start Commands

### Start Health Service API
```bash
cd health_svc
pip install -r requirements.txt
python main.py
```

### Start Telegram Bot
```bash
cd telegram_bot
pip install -r requirements.txt
export TELEGRAM_TOKEN=your_token
export HEALTH_SVC_API_URL=http://localhost:8000
python bot.py
```

### Test API
```bash
# Get patients
curl http://localhost:8000/api/v1/patients

# Create patient
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Patient"}'

# Get records
curl http://localhost:8000/api/v1/records?limit=5
```

---

## Key Benefits

1. ✅ **Separation of Concerns**: Database logic isolated from bot logic
2. ✅ **Scalability**: API can scale independently
3. ✅ **Reusability**: API usable by other clients
4. ✅ **Testability**: Easier to test each layer
5. ✅ **Maintainability**: Clear boundaries between components

---

## Migration Steps (High-Level)

1. Create `health_svc` folder structure
2. Move `storage/` from `telegram_bot/` to `health_svc/`
3. Create FastAPI service (routes, schemas, services)
4. Create HTTP client in `telegram_bot/clients/`
5. Update all handlers to use HTTP client
6. Update configuration files
7. Test end-to-end
8. Remove old `storage/` from `telegram_bot/`

---

## Support & Documentation

- **Full Plan**: See `REFACTORING_PLAN.md`
- **Implementation Details**: See `IMPLEMENTATION_GUIDE.md`
- **This Summary**: Quick reference for common patterns

---

## Notes

- Database schema remains unchanged
- Business logic remains unchanged
- Only the communication layer changes (direct DB → HTTP API)
- All existing data is compatible

