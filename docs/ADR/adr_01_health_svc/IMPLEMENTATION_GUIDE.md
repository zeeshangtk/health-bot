# Implementation Guide: Database Separation & REST API

This guide provides detailed code examples for implementing the refactoring plan.

---

## Part 1: Health Service Implementation

### 1.1 Service Configuration (`health_svc/config.py`)

```python
"""
Configuration module for Health Service API service.
"""
import os
from pathlib import Path

# Database Configuration
DATABASE_DIR = os.getenv("HEALTH_SVC_DB_DIR", "data")
DATABASE_FILE = os.getenv("HEALTH_SVC_DB_FILE", "health_bot.db")
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)

# Ensure database directory exists
Path(DATABASE_DIR).mkdir(parents=True, exist_ok=True)

# API Configuration
API_HOST = os.getenv("HEALTH_SVC_HOST", "0.0.0.0")
API_PORT = int(os.getenv("HEALTH_SVC_PORT", "8000"))
API_RELOAD = os.getenv("HEALTH_SVC_RELOAD", "false").lower() == "true"
```

### 1.2 Database Module (Moved from `telegram_bot/storage/`)

**File: `health_svc/storage/database.py`**

Key changes:
- Update import: `from config import DATABASE_DIR, DATABASE_PATH` → `from health_svc.config import DATABASE_DIR, DATABASE_PATH`
- Or use relative imports: `from ..config import DATABASE_DIR, DATABASE_PATH`

**File: `health_svc/storage/models.py`**

No changes needed - pure data model.

### 1.3 Pydantic Schemas (`health_svc/api/schemas.py`)

```python
"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""
    name: str = Field(..., min_length=1, max_length=200, description="Patient full name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe"
            }
        }


class PatientResponse(BaseModel):
    """Schema for patient response."""
    id: int
    name: str
    created_at: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "created_at": "2025-01-01 10:00:00"
            }
        }


class HealthRecordCreate(BaseModel):
    """Schema for creating a new health record."""
    timestamp: datetime
    patient: str = Field(..., min_length=1, max_length=200)
    record_type: str = Field(..., min_length=1, max_length=50)
    data_type: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-01T10:00:00",
                "patient": "John Doe",
                "record_type": "BP",
                "data_type": "text",
                "value": "120/80"
            }
        }


class HealthRecordResponse(BaseModel):
    """Schema for health record response."""
    timestamp: str  # ISO format string
    patient: str
    record_type: str
    data_type: str
    value: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-01T10:00:00",
                "patient": "John Doe",
                "record_type": "BP",
                "data_type": "text",
                "value": "120/80"
            }
        }
```

### 1.4 Service Layer (`health_svc/services/health_service.py`)

```python
"""
Service layer for health record operations.
"""
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
        """
        Save a health record.
        
        Returns:
            Dict with 'success' bool and either 'record' (HealthRecordResponse) 
            or 'message' (error message)
        """
        try:
            record_id = self.db.save_record(
                timestamp=timestamp,
                patient=patient,
                record_type=record_type,
                data_type=data_type,
                value=value
            )
            
            # Fetch the saved record to return full details
            # Get the most recent record for this patient (should be the one we just saved)
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

### 1.5 Service Layer (`health_svc/services/patient_service.py`)

```python
"""
Service layer for patient operations.
"""
from typing import List, Dict, Any, Optional
from storage.database import Database, get_database
from api.schemas import PatientResponse


class PatientService:
    """Service layer for patient operations."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
    
    def add_patient(self, name: str) -> Dict[str, Any]:
        """
        Add a new patient.
        
        Returns:
            Dict with 'success' bool and either 'patient' (PatientResponse) 
            or 'message' (error message)
        """
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

### 1.6 FastAPI Routes (`health_svc/api/routes.py`)

```python
"""
FastAPI route definitions for Health Service API.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from api.schemas import (
    HealthRecordCreate,
    HealthRecordResponse,
    PatientCreate,
    PatientResponse
)
from services.health_service import HealthService
from services.patient_service import PatientService

router = APIRouter()

# Initialize services
health_service = HealthService()
patient_service = PatientService()


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Health Service API", "version": "1.0.0"}


# Patient Endpoints
@router.post("/api/v1/patients", response_model=PatientResponse, status_code=201)
async def create_patient(patient: PatientCreate):
    """Create a new patient."""
    result = patient_service.add_patient(patient.name)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result["patient"]


@router.get("/api/v1/patients", response_model=List[PatientResponse])
async def list_patients():
    """Get all patients, sorted alphabetically."""
    return patient_service.get_patients()


# Health Record Endpoints
@router.post("/api/v1/records", response_model=HealthRecordResponse, status_code=201)
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


@router.get("/api/v1/records", response_model=List[HealthRecordResponse])
async def list_records(
    patient: Optional[str] = Query(None, description="Filter by patient name"),
    record_type: Optional[str] = Query(None, description="Filter by record type"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results")
):
    """Get health records with optional filters."""
    records = health_service.get_records(
        patient=patient,
        record_type=record_type,
        limit=limit
    )
    return records
```

### 1.7 FastAPI Main Application (`health_svc/main.py`)

```python
"""
FastAPI application entry point for Health Service API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import API_HOST, API_PORT, API_RELOAD
from api.routes import router

# Create FastAPI app
app = FastAPI(
    title="Health Service API",
    description="REST API for health record management",
    version="1.0.0"
)

# Configure CORS to allow telegram_bot to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    from storage.database import get_database
    # This will initialize the database schema
    get_database()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
```

### 1.8 Requirements (`health_svc/requirements.txt`)

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

---

## Part 2: Telegram Bot Client Implementation

### 2.1 HTTP Client (`telegram_bot/clients/health_api_client.py`)

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
            raise ValueError("HEALTH_SVC_API_URL must be set in config")
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Raises:
            httpx.HTTPStatusError: For HTTP error responses
            httpx.RequestError: For connection/request errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"API error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Request error: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e
    
    # Patient methods
    async def add_patient(self, name: str) -> Dict[str, Any]:
        """
        Add a new patient.
        
        Returns:
            Dict with patient data (id, name, created_at)
        
        Raises:
            ValueError: If patient already exists or API error
            ConnectionError: If connection fails
        """
        return await self._request(
            "POST",
            "/api/v1/patients",
            json={"name": name}
        )
    
    async def get_patients(self) -> List[Dict[str, Any]]:
        """
        Get all patients.
        
        Returns:
            List of patient dicts with id, name, created_at
        
        Raises:
            ConnectionError: If connection fails
        """
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
        """
        Save a health record.
        
        Returns:
            Dict with record data (timestamp, patient, record_type, data_type, value)
        
        Raises:
            ValueError: If patient not found or API error
            ConnectionError: If connection fails
        """
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
        """
        Get health records with optional filters.
        
        Args:
            patient: Filter by patient name (optional)
            record_type: Filter by record type (optional)
            limit: Limit number of results (optional)
        
        Returns:
            List of record dicts
        
        Raises:
            ConnectionError: If connection fails
        """
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

### 2.2 Updated Configuration (`telegram_bot/config.py`)

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

---

## Part 3: Handler Updates

### 3.1 Updated `add_record.py` Handler

**Key Changes:**
- Replace `from storage.database import get_database` with `from clients.health_api_client import get_health_api_client`
- Replace `db = get_database()` with `client = get_health_api_client()`
- Replace `db.get_patients()` with `await client.get_patients()`
- Replace `db.save_record(...)` with `await client.save_record(...)`
- Update response handling (API returns dicts, not objects)

**Example snippet:**
```python
# OLD:
db = get_database()
patients = db.get_patients()
patient_names = [patient["name"] for patient in patients]

# NEW:
client = get_health_api_client()
patients = await client.get_patients()
patient_names = [patient["name"] for patient in patients]
```

**Full updated function example:**
```python
async def add_record_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /add_record command."""
    client = get_health_api_client()
    
    try:
        patients = await client.get_patients()
    except (ValueError, ConnectionError) as e:
        logger.error(f"Error fetching patients: {e}")
        await update.message.reply_text(
            "❌ Error connecting to health service. Please try again later."
        )
        return ConversationHandler.END
    
    if not patients:
        await update.message.reply_text(
            "❌ No patients found. Please add a patient first using /add_patient."
        )
        return ConversationHandler.END
    
    # Extract patient names from dicts
    patient_names = [patient["name"] for patient in patients]
    
    # ... rest of the function remains the same ...
```

**Updated save logic:**
```python
# OLD:
db = get_database()
record_id = db.save_record(
    timestamp=timestamp,
    patient=patient_name,
    record_type=record_type,
    data_type="text",
    value=value_text
)

# NEW:
client = get_health_api_client()
try:
    result = await client.save_record(
        timestamp=timestamp,
        patient=patient_name,
        record_type=record_type,
        data_type="text",
        value=value_text
    )
    # result is a dict with timestamp, patient, record_type, data_type, value
except (ValueError, ConnectionError) as e:
    logger.error(f"Error saving record: {e}")
    await update.message.reply_text(
        "❌ Error saving record. Please try again or contact support."
    )
    return ENTERING_VALUE
```

### 3.2 Updated `add_patient.py` Handler

```python
# OLD:
db = get_database()
success = db.add_patient(patient_name)

# NEW:
client = get_health_api_client()
try:
    result = await client.add_patient(patient_name)
    # result contains: {"id": 1, "name": "...", "created_at": "..."}
    success = True
except ValueError as e:
    # Patient already exists or other API error
    success = False
    error_message = str(e)
except ConnectionError as e:
    logger.error(f"Connection error: {e}")
    await update.message.reply_text(
        "❌ Error connecting to health service. Please try again later."
    )
    return WAITING_FOR_NAME
```

### 3.3 Updated `get_patients.py` Handler

```python
# OLD:
db = get_database()
patients = db.get_patients()

# NEW:
client = get_health_api_client()
try:
    patients = await client.get_patients()
except ConnectionError as e:
    logger.error(f"Connection error: {e}")
    await update.message.reply_text(
        "❌ Error connecting to health service. Please try again later."
    )
    return
```

### 3.4 Updated `view.py` Handler

```python
# OLD:
db = get_database()
patients = db.get_patients()
records = db.get_records(patient=patient_filter, record_type=type_filter, limit=5)

# NEW:
client = get_health_api_client()
try:
    patients = await client.get_patients()
    records = await client.get_records(
        patient=patient_filter,
        record_type=type_filter,
        limit=5
    )
except ConnectionError as e:
    logger.error(f"Connection error: {e}")
    await query.edit_message_text(
        "❌ Error connecting to health service. Please try again later."
    )
    return ConversationHandler.END
```

**Note:** API returns dicts, so update record access:
```python
# OLD:
record.timestamp  # datetime object
record.patient
record.record_type
record.value

# NEW:
from datetime import datetime
timestamp = datetime.fromisoformat(record["timestamp"])  # Parse ISO string
patient = record["patient"]
record_type = record["record_type"]
value = record["value"]
```

### 3.5 Updated `export.py` Handler

Similar changes as `view.py`:
- Replace `get_database()` with `get_health_api_client()`
- Use `await client.get_patients()` and `await client.get_records()`
- Parse timestamp strings from API responses

---

## Part 4: Testing

### 4.1 Test Health Service API

```python
# health_svc/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_patient():
    response = client.post("/api/v1/patients", json={"name": "Test Patient"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test Patient"

def test_get_patients():
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### 4.2 Test Telegram Bot Client

```python
# telegram_bot/tests/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from clients.health_api_client import HealthAPIClient

@pytest.mark.asyncio
async def test_get_patients():
    client = HealthAPIClient(base_url="http://test-server")
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = [{"id": 1, "name": "Test", "created_at": "2025-01-01"}]
        mock_response.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
        
        result = await client.get_patients()
        assert len(result) == 1
        assert result[0]["name"] == "Test"
```

---

## Part 5: Running the Services

### 5.1 Start Health Service API

```bash
cd health_svc
pip install -r requirements.txt
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.2 Start Telegram Bot

```bash
cd telegram_bot
pip install -r requirements.txt
export TELEGRAM_TOKEN=your_token
export HEALTH_SVC_API_URL=http://localhost:8000
python bot.py
```

### 5.3 Verify API is Running

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/v1/patients
```

---

## Part 6: Error Handling Best Practices

### 6.1 Client Error Handling

The HTTP client should handle:
- **Connection errors**: Network issues, service down
- **Timeout errors**: Service too slow
- **HTTP errors**: 400, 404, 409, 500, etc.
- **Invalid responses**: Malformed JSON

### 6.2 Handler Error Handling

Each handler should:
- Catch `ConnectionError` for network issues
- Catch `ValueError` for API/business logic errors
- Provide user-friendly error messages
- Log errors for debugging

### 6.3 Retry Logic (Optional)

For production, consider adding retry logic:
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_patients_with_retry(client):
    return await client.get_patients()
```

---

## Summary

This implementation guide provides:
1. Complete FastAPI service implementation
2. HTTP client for telegram bot
3. Updated handler examples
4. Testing strategies
5. Error handling patterns
6. Deployment instructions

Follow the refactoring plan step-by-step, using these code examples as reference.

