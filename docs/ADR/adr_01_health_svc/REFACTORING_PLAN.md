# Health Bot Refactoring Plan: Database Separation & REST API

## Executive Summary

This document outlines a comprehensive refactoring plan to extract all database-related logic from the `telegram_bot` folder into a new `health_svc` service. The new service will expose a FastAPI-based REST API that the Telegram bot will consume, creating a clean separation of concerns.

---

## 1. Current Architecture Analysis

### 1.1 Database Operations Identified

#### Core Database Layer (`telegram_bot/storage/`)
- **`database.py`**: Contains the `Database` class with all SQLite operations
  - `_init_db()`: Schema initialization and migration logic
  - `_migrate_to_foreign_key()`: Database migration helper
  - `save_record()`: Insert health records
  - `get_records()`: Query health records with filters (patient, record_type, limit)
  - `add_patient()`: Insert new patients
  - `get_patients()`: Retrieve all patients

- **`models.py`**: Contains `HealthRecord` data model class

#### Database Usage in Handlers
- **`handlers/add_record.py`**: 
  - `get_database()` → `db.get_patients()` (line 32-33)
  - `get_database()` → `db.get_patients()` (line 79-80)
  - `get_database()` → `db.save_record()` (line 193-201)

- **`handlers/add_patient.py`**:
  - `get_database()` → `db.add_patient()` (line 46-47)
  - `get_database()` → `db.get_patients()` (line 80)

- **`handlers/get_patients.py`**:
  - `get_database()` → `db.get_patients()` (line 19-20)

- **`handlers/view.py`**:
  - `get_database()` → `db.get_patients()` (line 29-30, 75-76)
  - `get_database()` → `db.get_records()` (line 149-159)

- **`handlers/export.py`**:
  - `get_database()` → `db.get_patients()` (line 34-35, 80-81)
  - `get_database()` → `db.get_records()` (line 200-205)

### 1.2 Current Dependencies
- SQLite3 (Python standard library)
- Direct database connections in handlers
- Global database instance via `get_database()` function

---

## 2. Target Architecture

### 2.1 New Folder Structure

```
health-bot/
├── telegram_bot/                    # Telegram bot client (no DB access)
│   ├── bot.py
│   ├── config.py                    # Updated: Remove DB config, add API URL
│   ├── handlers/                    # Updated: Use HTTP client instead of DB
│   │   ├── add_record.py
│   │   ├── add_patient.py
│   │   ├── get_patients.py
│   │   ├── view.py
│   │   └── export.py
│   ├── clients/                     # NEW: HTTP client for API calls
│   │   ├── __init__.py
│   │   └── health_api_client.py
│   └── requirements.txt             # Updated: Add httpx
│
├── health_svc/                   # NEW: Database service with REST API
│   ├── __init__.py
│   ├── main.py                      # FastAPI application
│   ├── config.py                    # Service configuration
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── health_record.py         # HealthRecord model
│   │   └── patient.py               # Patient model (if needed)
│   ├── storage/                     # Database layer (moved from telegram_bot)
│   │   ├── __init__.py
│   │   ├── database.py              # Database class (moved)
│   │   └── models.py                # Models (moved)
│   ├── api/                         # FastAPI routes
│   │   ├── __init__.py
│   │   ├── routes.py                # Main route definitions
│   │   └── schemas.py               # Pydantic schemas for request/response
│   ├── services/                    # Business logic layer (optional)
│   │   ├── __init__.py
│   │   ├── health_service.py        # Service layer wrapping DB operations
│   │   └── patient_service.py
│   ├── requirements.txt             # FastAPI, uvicorn, etc.
│   └── README.md
│
└── data/                            # Shared database location (or move to health_svc)
    └── health_bot.db
```

### 2.2 Architecture Diagram

```
┌─────────────────────────────────┐
│   Telegram Bot (telegram_bot)   │
│                                 │
│  ┌──────────────────────────┐   │
│  │   HTTP Client            │   │
│  │   (health_api_client)   │   │
│  └──────────┬───────────────┘   │
│             │ HTTP/REST          │
└─────────────┼────────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Health Service API (health_svc)│
│                                 │
│  ┌──────────────────────────┐   │
│  │   FastAPI Routes         │   │
│  │   (api/routes.py)       │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │   Service Layer          │   │
│  │   (services/)            │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │   Database Layer         │   │
│  │   (storage/database.py)  │   │
│  └──────────┬───────────────┘   │
│             │                    │
└─────────────┼────────────────────┘
              │
              ▼
      ┌───────────────┐
      │  SQLite DB    │
      │ health_bot.db │
      └───────────────┘
```

---

## 3. Step-by-Step Refactoring Instructions

### Phase 1: Create Health Service Structure

#### Step 1.1: Create Base Folder Structure
```bash
mkdir -p health_svc/{api,services,storage,models}
touch health_svc/__init__.py
touch health_svc/main.py
touch health_svc/config.py
touch health_svc/api/__init__.py
touch health_svc/api/routes.py
touch health_svc/api/schemas.py
touch health_svc/services/__init__.py
touch health_svc/services/health_service.py
touch health_svc/services/patient_service.py
touch health_svc/models/__init__.py
touch health_svc/requirements.txt
touch health_svc/README.md
```

#### Step 1.2: Move Database Code
- Copy `telegram_bot/storage/database.py` → `health_svc/storage/database.py`
- Copy `telegram_bot/storage/models.py` → `health_svc/storage/models.py`
- Update imports in moved files to remove `telegram_bot` dependencies

#### Step 1.3: Create Configuration
Create `health_svc/config.py`:
```python
import os
from pathlib import Path

# Database Configuration
DATABASE_DIR = os.getenv("HEALTH_SVC_DB_DIR", "data")
DATABASE_FILE = os.getenv("HEALTH_SVC_DB_FILE", "health_bot.db")
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)

# API Configuration
API_HOST = os.getenv("HEALTH_SVC_HOST", "0.0.0.0")
API_PORT = int(os.getenv("HEALTH_SVC_PORT", "8000"))
API_RELOAD = os.getenv("HEALTH_SVC_RELOAD", "false").lower() == "true"
```

### Phase 2: Implement FastAPI Service

#### Step 2.1: Create Pydantic Schemas
Create `health_svc/api/schemas.py` with request/response models.

#### Step 2.2: Create Service Layer
Create service classes that wrap database operations for better abstraction.

#### Step 2.3: Create FastAPI Routes
Create REST endpoints matching all database operations.

#### Step 2.4: Create FastAPI Application
Create `health_svc/main.py` with FastAPI app initialization.

### Phase 3: Create HTTP Client for Telegram Bot

#### Step 3.1: Create Client Module
Create `telegram_bot/clients/health_api_client.py` with HTTP client class.

#### Step 3.2: Update Configuration
Update `telegram_bot/config.py` to include API URL and remove DB config.

### Phase 4: Update Telegram Bot Handlers

#### Step 4.1: Replace Database Calls
Update all handlers to use HTTP client instead of direct database access.

#### Step 4.2: Update Imports
Remove `storage.database` imports, add `clients.health_api_client` imports.

### Phase 5: Testing & Validation

#### Step 5.1: Update Tests
- Move database tests to `health_svc/tests/`
- Create integration tests for API endpoints
- Update telegram bot tests to mock HTTP client

#### Step 5.2: Environment Setup
- Create `.env.example` files for both services
- Update documentation

---

## 4. Detailed Implementation

### 4.1 FastAPI Routes (`health_svc/api/routes.py`)

```python
from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from api.schemas import (
    HealthRecordCreate,
    HealthRecordResponse,
    PatientCreate,
    PatientResponse,
    RecordsQueryParams
)
from services.health_service import HealthService
from services.patient_service import PatientService

app = FastAPI(title="Health Service API", version="1.0.0")

# Initialize services
health_service = HealthService()
patient_service = PatientService()


@app.get("/")
async def root():
    return {"message": "Health Service API", "version": "1.0.0"}


# Patient Endpoints
@app.post("/api/v1/patients", response_model=PatientResponse, status_code=201)
async def create_patient(patient: PatientCreate):
    """Create a new patient."""
    result = patient_service.add_patient(patient.name)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result["patient"]


@app.get("/api/v1/patients", response_model=List[PatientResponse])
async def list_patients():
    """Get all patients."""
    return patient_service.get_patients()


# Health Record Endpoints
@app.post("/api/v1/records", response_model=HealthRecordResponse, status_code=201)
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


@app.get("/api/v1/records", response_model=List[HealthRecordResponse])
async def list_records(
    patient: Optional[str] = Query(None, description="Filter by patient name"),
    record_type: Optional[str] = Query(None, description="Filter by record type"),
    limit: Optional[int] = Query(None, ge=1, description="Limit number of results")
):
    """Get health records with optional filters."""
    records = health_service.get_records(
        patient=patient,
        record_type=record_type,
        limit=limit
    )
    return records
```

### 4.2 Pydantic Schemas (`health_svc/api/schemas.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Patient full name")


class PatientResponse(BaseModel):
    id: int
    name: str
    created_at: str

    class Config:
        from_attributes = True


class HealthRecordCreate(BaseModel):
    timestamp: datetime
    patient: str = Field(..., min_length=1)
    record_type: str = Field(..., min_length=1)
    data_type: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


class HealthRecordResponse(BaseModel):
    timestamp: str  # ISO format string
    patient: str
    record_type: str
    data_type: str
    value: str

    class Config:
        from_attributes = True
```

### 4.3 Service Layer (`health_svc/services/health_service.py`)

```python
from typing import Optional, List, Dict, Any
from datetime import datetime

from storage.database import Database, get_database
from storage.models import HealthRecord
from api.schemas import HealthRecordResponse


class HealthService:
    """Service layer for health record operations."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
    
    def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        data_type: str,
        value: str
    ) -> Dict[str, Any]:
        """Save a health record."""
        try:
            record_id = self.db.save_record(
                timestamp=timestamp,
                patient=patient,
                record_type=record_type,
                data_type=data_type,
                value=value
            )
            
            # Fetch the saved record to return full details
            records = self.db.get_records(patient=patient, limit=1)
            if records:
                record = records[0]
                return {
                    "success": True,
                    "record": HealthRecordResponse(
                        timestamp=record.timestamp.isoformat(),
                        patient=record.patient,
                        record_type=record.record_type,
                        data_type=record.data_type,
                        value=record.value
                    )
                }
            else:
                return {
                    "success": False,
                    "message": "Record saved but could not be retrieved"
                }
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            return {"success": False, "message": f"Database error: {str(e)}"}
    
    def get_records(
        self,
        patient: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[HealthRecordResponse]:
        """Get health records with filters."""
        records = self.db.get_records(
            patient=patient,
            record_type=record_type,
            limit=limit
        )
        
        return [
            HealthRecordResponse(
                timestamp=record.timestamp.isoformat(),
                patient=record.patient,
                record_type=record.record_type,
                data_type=record.data_type,
                value=record.value
            )
            for record in records
        ]
```

### 4.4 Service Layer (`health_svc/services/patient_service.py`)

```python
from typing import List, Dict, Any
from storage.database import Database, get_database
from api.schemas import PatientResponse


class PatientService:
    """Service layer for patient operations."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
    
    def add_patient(self, name: str) -> Dict[str, Any]:
        """Add a new patient."""
        success = self.db.add_patient(name)
        
        if success:
            # Fetch the created patient
            patients = self.db.get_patients()
            created_patient = next((p for p in patients if p["name"] == name), None)
            
            if created_patient:
                return {
                    "success": True,
                    "patient": PatientResponse(
                        id=created_patient["id"],
                        name=created_patient["name"],
                        created_at=created_patient["created_at"]
                    )
                }
            else:
                return {
                    "success": False,
                    "message": "Patient created but could not be retrieved"
                }
        else:
            return {
                "success": False,
                "message": f"Patient '{name}' already exists"
            }
    
    def get_patients(self) -> List[PatientResponse]:
        """Get all patients."""
        patients = self.db.get_patients()
        return [
            PatientResponse(
                id=p["id"],
                name=p["name"],
                created_at=p["created_at"]
            )
            for p in patients
        ]
```

### 4.5 FastAPI Main Application (`health_svc/main.py`)

```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_HOST, API_PORT, API_RELOAD
from api.routes import app

# Configure CORS (allow telegram_bot to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
```

### 4.6 HTTP Client (`telegram_bot/clients/health_api_client.py`)

```python
"""
HTTP client for Health Service API.
Provides a clean interface for telegram_bot to interact with the health_svc service.
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from config import HEALTH_SVC_API_URL

logger = logging.getLogger(__name__)


class HealthAPIClient:
    """Client for Health Service REST API."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or HEALTH_SVC_API_URL
        if not self.base_url:
            raise ValueError("HEALTH_SVC_API_URL must be set")
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API error {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
    
    # Patient methods
    async def add_patient(self, name: str) -> Dict[str, Any]:
        """Add a new patient."""
        return await self._request(
            "POST",
            "/api/v1/patients",
            json={"name": name}
        )
    
    async def get_patients(self) -> List[Dict[str, Any]]:
        """Get all patients."""
        return await self._request("GET", "/api/v1/patients")
    
    # Health record methods
    async def save_record(
        self,
        timestamp: datetime,
        patient: str,
        record_type: str,
        data_type: str,
        value: str
    ) -> Dict[str, Any]:
        """Save a health record."""
        return await self._request(
            "POST",
            "/api/v1/records",
            json={
                "timestamp": timestamp.isoformat(),
                "patient": patient,
                "record_type": record_type,
                "data_type": data_type,
                "value": value
            }
        )
    
    async def get_records(
        self,
        patient: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get health records with optional filters."""
        params = {}
        if patient:
            params["patient"] = patient
        if record_type:
            params["record_type"] = record_type
        if limit:
            params["limit"] = limit
        
        return await self._request("GET", "/api/v1/records", params=params)


# Global client instance
_client_instance: Optional[HealthAPIClient] = None


def get_health_api_client() -> HealthAPIClient:
    """Get or create the global API client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = HealthAPIClient()
    return _client_instance
```

### 4.7 Updated Telegram Bot Configuration (`telegram_bot/config.py`)

```python
"""
Configuration module for health bot.
Updated to use REST API instead of direct database access.
"""
import os
from typing import List

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Health Service API Configuration
HEALTH_SVC_API_URL = os.getenv(
    "HEALTH_SVC_API_URL",
    "http://localhost:8000"
)

# Supported Record Types
SUPPORTED_RECORD_TYPES: List[str] = [
    "BP",          # Blood Pressure
    "Sugar",       # Blood Sugar
    "Creatinine",  # Creatinine level
    "Weight",      # Weight measurement
    "Other"        # Other health records
]


def load_env():
    """
    Load configuration from environment variables.
    
    Environment variables:
        TELEGRAM_TOKEN: The Telegram bot token (required)
        HEALTH_SVC_API_URL: URL of the Health Service API (default: http://localhost:8000)
    
    Returns:
        bool: True if token is available, False otherwise
    """
    return TELEGRAM_TOKEN is not None
```

### 4.8 Updated Handler Example (`telegram_bot/handlers/add_record.py`)

**Before:**
```python
from storage.database import get_database

db = get_database()
patients = db.get_patients()
record_id = db.save_record(...)
```

**After:**
```python
from clients.health_api_client import get_health_api_client

client = get_health_api_client()
patients = await client.get_patients()
result = await client.save_record(...)
```

---

## 5. Environment Variables

### 5.1 Health Service (`.env` or environment)

```bash
# Database
HEALTH_SVC_DB_DIR=data
HEALTH_SVC_DB_FILE=health_bot.db

# API Server
HEALTH_SVC_HOST=0.0.0.0
HEALTH_SVC_PORT=8000
HEALTH_SVC_RELOAD=false
```

### 5.2 Telegram Bot (`.env` or environment)

```bash
# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token

# Health Service API
HEALTH_SVC_API_URL=http://localhost:8000
```

---

## 6. Updated Requirements

### 6.1 `health_svc/requirements.txt`

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

### 6.2 `telegram_bot/requirements.txt` (Updated)

```txt
python-telegram-bot>=20.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.25.0  # NEW: For HTTP client
```

---

## 7. Migration Checklist

- [ ] Create `health_svc` folder structure
- [ ] Move `storage/` from `telegram_bot/` to `health_svc/`
- [ ] Update imports in moved database files
- [ ] Create FastAPI application structure
- [ ] Implement Pydantic schemas
- [ ] Implement service layer
- [ ] Implement FastAPI routes
- [ ] Create HTTP client in `telegram_bot/clients/`
- [ ] Update `telegram_bot/config.py`
- [ ] Update all handler files to use HTTP client
- [ ] Remove `storage/` folder from `telegram_bot/`
- [ ] Update tests
- [ ] Create environment variable documentation
- [ ] Test end-to-end flow
- [ ] Update README files

---

## 8. Testing Strategy

### 8.1 Health Service Tests
- Unit tests for database operations
- Unit tests for service layer
- Integration tests for API endpoints
- Test error handling and edge cases

### 8.2 Telegram Bot Tests
- Mock HTTP client in handler tests
- Test error handling for API failures
- Test retry logic (if implemented)

---

## 9. Deployment Considerations

### 9.1 Running Services

**Health Service API:**
```bash
cd health_svc
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Telegram Bot:**
```bash
cd telegram_bot
python bot.py
```

### 9.2 Docker (Optional Future Enhancement)

Both services can be containerized separately, allowing independent scaling and deployment.

---

## 10. Backwards Compatibility Notes

- **Database Schema**: No changes to database schema
- **Data Location**: Database can remain in `data/` folder or move to `health_svc/data/`
- **Business Logic**: All business logic remains unchanged, only location changes
- **API Compatibility**: New REST API matches existing database operations exactly

---

## 11. Benefits of This Refactoring

1. **Separation of Concerns**: Database logic separated from bot logic
2. **Scalability**: API can be scaled independently
3. **Testability**: Easier to test each layer independently
4. **Reusability**: API can be used by other clients (web app, mobile app, etc.)
5. **Maintainability**: Clear boundaries between components
6. **Technology Flexibility**: Can swap database or add caching without affecting bot

---

## 12. Next Steps

1. Review and approve this plan
2. Create feature branch for refactoring
3. Execute Phase 1 (Create structure)
4. Execute Phase 2 (Implement API)
5. Execute Phase 3 (Create client)
6. Execute Phase 4 (Update handlers)
7. Execute Phase 5 (Testing)
8. Merge to main branch

---

## Appendix: Code Snippets Summary

### Key Changes in Handlers

**Pattern to Replace:**
```python
from storage.database import get_database
db = get_database()
result = db.some_method()
```

**New Pattern:**
```python
from clients.health_api_client import get_health_api_client
client = get_health_api_client()
result = await client.some_method()
```

### Error Handling

The HTTP client should handle:
- Connection errors
- Timeout errors
- HTTP error status codes
- Invalid responses

Consider implementing retry logic for transient failures.

