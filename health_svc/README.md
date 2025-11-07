# Health Service API

FastAPI REST service for health record management. This service provides a RESTful API for tracking and managing patient health records including blood pressure, weight, temperature, and other measurements.

## 🚀 Quick Start

### Prerequisites

- Python 3.13+ (or compatible version)
- Virtual environment activated

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Configuration

Environment variables (with defaults):
- `HEALTH_SVC_HOST` - API host (default: `0.0.0.0`)
- `HEALTH_SVC_PORT` - API port (default: `8000`)
- `HEALTH_SVC_DB_DIR` - Database directory (default: `data`)
- `HEALTH_SVC_DB_FILE` - Database filename (default: `health_bot.db`)
- `HEALTH_SVC_RELOAD` - Enable auto-reload (default: `false`)

### Running the Server

```bash
# Start the API server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 Interactive API Documentation

The Health Service API includes **automatic interactive documentation** powered by FastAPI. Once the server is running, you can access the documentation in your browser.

### Swagger UI

**URL:** [http://localhost:8000/docs](http://localhost:8000/docs)

Swagger UI provides an interactive interface where you can:
- **Browse all available endpoints** organized by tags (Patients, Health Records, Health)
- **View request/response schemas** with detailed field descriptions
- **Test endpoints directly** by clicking "Try it out" on any endpoint
- **See example requests and responses** for each endpoint
- **Validate your requests** before sending them

**Features:**
- ✅ Click-to-test functionality
- ✅ Request body editor with validation
- ✅ Query parameter inputs
- ✅ Response preview with formatted JSON
- ✅ Error handling examples
- ✅ Authentication support (if configured)

## 🔌 API Endpoints

### Health Check

- **GET /** - API information and version

### Patient Management

- **POST /api/v1/patients** - Create a new patient
  - Request body: `{"name": "John Doe"}`
  - Returns: Patient object with ID and creation timestamp
  - Status: 201 Created (or 409 Conflict if patient exists)

- **GET /api/v1/patients** - List all patients
  - Returns: Array of patient objects, sorted alphabetically

### Health Records

- **POST /api/v1/records** - Create a new health record
  - Request body:
    ```json
    {
      "timestamp": "2025-01-01T10:00:00",
      "patient": "John Doe",
      "record_type": "BP",
      "data_type": "text",
      "value": "120/80"
    }
    ```
  - Returns: Created health record
  - Status: 201 Created (or 400 Bad Request if validation fails)

- **GET /api/v1/records** - List health records with optional filters
  - Query parameters:
    - `patient` (optional): Filter by patient name
    - `record_type` (optional): Filter by record type (e.g., "BP", "Weight")
    - `limit` (optional): Maximum number of results (1-1000)
  - Returns: Array of health record objects

## 🧪 Testing Endpoints

### Using Swagger UI (Easiest)

1. Start the server: `python main.py`
2. Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser
3. Click on any endpoint to expand it
4. Click "Try it out" button
5. Fill in the request parameters/body
6. Click "Execute" to send the request
7. View the response below

### Using cURL

```bash
# Health check
curl http://localhost:8000/

# Create a patient
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}'

# List all patients
curl http://localhost:8000/api/v1/patients

# Create a health record
curl -X POST http://localhost:8000/api/v1/records \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2025-01-01T10:00:00",
    "patient": "John Doe",
    "record_type": "BP",
    "data_type": "text",
    "value": "120/80"
  }'

# List health records (with filters)
curl "http://localhost:8000/api/v1/records?patient=John%20Doe&record_type=BP&limit=10"
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a patient
response = requests.post(
    f"{BASE_URL}/api/v1/patients",
    json={"name": "John Doe"}
)
print(response.json())

# List patients
response = requests.get(f"{BASE_URL}/api/v1/patients")
print(response.json())

# Create a health record
response = requests.post(
    f"{BASE_URL}/api/v1/records",
    json={
        "timestamp": "2025-01-01T10:00:00",
        "patient": "John Doe",
        "record_type": "BP",
        "data_type": "text",
        "value": "120/80"
    }
)
print(response.json())
```

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_api.py -v
```

## 🗄️ Database

The service uses SQLite for data storage. The database is automatically initialized on first use.

- **Location:** `data/health_bot.db`
- **Tables:**
  - `patients` - Patient information
  - `health_records` - Health measurement records

### Database Migration

```bash
# Check migration status
python migrate_db.py --status

# Run migration with backup
python migrate_db.py --backup

# Dry run (test without changes)
python migrate_db.py --dry-run
```

## 📖 Project Structure

```
health_svc/
├── api/                    # API layer
│   ├── routes.py          # FastAPI route definitions
│   └── schemas.py         # Pydantic request/response models
├── services/              # Business logic layer
│   ├── health_service.py  # Health record operations
│   └── patient_service.py # Patient operations
├── storage/               # Database layer
│   ├── database.py       # Database connection and operations
│   └── models.py         # SQLAlchemy models
├── tests/                # Unit tests
├── main.py               # FastAPI application entry point
├── config.py             # Configuration management
├── migrate_db.py         # Database migration script
└── requirements.txt      # Python dependencies
```

## 🔧 Development

### Code Style

The project follows Python best practices:
- Type hints for all function parameters and returns
- Pydantic models for request/response validation
- Comprehensive docstrings for all endpoints
- Clear separation of concerns (API, services, storage)

### Adding New Endpoints

1. Define Pydantic schemas in `api/schemas.py`
2. Add route handler in `api/routes.py` with proper tags and descriptions
3. Implement business logic in appropriate service class
4. Add tests in `tests/test_api.py`
5. Test in Swagger UI at `/docs`

## 🔒 Security Notes

- CORS is configured to allow all origins (configure for production)
- No authentication is currently implemented (add for production)
- Database uses SQLite (consider PostgreSQL for production)
- Never commit sensitive data or tokens to version control

## 📝 License

[Add your license here]

