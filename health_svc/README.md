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
- `HEALTH_SVC_UPLOAD_DIR` - Upload directory (default: `uploads`)
- `HEALTH_SVC_UPLOAD_MAX_SIZE` - Max upload size in bytes (default: `10485760` = 10MB)
- `HEALTH_SVC_REDIS_URL` - Redis connection URL (default: `redis://localhost:6379`)
- `HEALTH_SVC_REDIS_DB` - Redis database number (default: `0`)
- `HEALTH_SVC_CELERY_TASK_SERIALIZER` - Task serializer (default: `json`)
- `HEALTH_SVC_CELERY_RESULT_SERIALIZER` - Result serializer (default: `json`)
- `HEALTH_SVC_CELERY_ACCEPT_CONTENT` - Accepted content types (default: `json`)
- `HEALTH_SVC_CELERY_TIMEZONE` - Timezone for tasks (default: `UTC`)
- `HEALTH_SVC_CELERY_ENABLE_UTC` - Enable UTC (default: `true`)

### Running the Server

#### Basic Setup (Without Background Tasks)

```bash
# Start the API server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Full Setup (With Celery Background Tasks)

For full functionality including background processing of uploaded files:

1. **Start Redis** (required for Celery):
   ```bash
   # Using Docker (recommended)
   docker run -d -p 6379:6379 redis
   
   # Or install and run locally
   redis-server
   ```

2. **Start Celery Worker** (processes background tasks):
   ```bash
   # From the health_svc directory
   celery -A celery_app worker --loglevel=info
   ```

3. **Start Flower** (optional, for monitoring):
   ```bash
   # From the health_svc directory
   celery -A celery_app flower --port=5555
   ```
   Then access Flower UI at: http://localhost:5555

4. **Start FastAPI Server**:
   ```bash
   python main.py
   # Or
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

**Note**: The API will work without Redis/Celery, but background processing tasks will not be queued. File uploads will still succeed, but the `task_id` in the response will be `null`.

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

- **POST /api/v1/records/upload** - Upload an image file
  - Request: Multipart form data with image file (JPEG, PNG, GIF, or BMP)
  - Maximum file size: 10MB
  - Returns: Upload status, filename, and optional task_id for background processing
  - Example response:
    ```json
    {
      "status": "success",
      "filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
      "message": "Image uploaded successfully",
      "task_id": "abc123-task-id"
    }
    ```
  - The `task_id` is included when Celery is configured and the background processing task is successfully queued

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
├── tasks/                 # Celery background tasks
│   ├── __init__.py       # Tasks module initialization
│   └── upload_tasks.py   # File upload processing tasks
├── tests/                # Unit tests
├── main.py               # FastAPI application entry point
├── config.py             # Configuration management
├── celery_app.py         # Celery application instance
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

## 🔄 Background Processing

The service uses Celery for asynchronous background processing of uploaded files. After a file is successfully saved to disk, a background task is queued for post-processing.

### Task Processing

The `process_uploaded_file` task performs:
- File validation and verification
- Metadata extraction (can be extended)
- Logging of upload events
- Error handling with automatic retries (up to 3 attempts with exponential backoff)

### Monitoring Tasks

Use Flower to monitor task execution:
- Access Flower UI at http://localhost:5555 (when running)
- View task status, execution time, and results
- Monitor worker health and task queues
- Debug failed tasks and retries

### Task Status

You can check task status using the task_id returned in the upload response:
```python
from celery_app import celery_app

# Get task result
task = celery_app.AsyncResult(task_id)
print(task.state)  # PENDING, SUCCESS, FAILURE, etc.
print(task.result)  # Task result when completed
```

## 🔒 Security Notes

- CORS is configured to allow all origins (configure for production)
- No authentication is currently implemented (add for production)
- Database uses SQLite (consider PostgreSQL for production)
- Redis should be secured in production (use password authentication)
- Never commit sensitive data or tokens to version control

## 📝 License

[Add your license here]

