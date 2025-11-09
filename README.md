# Health Bot - Family Medical Measurements Tracker

A microservices-based health tracking system consisting of a Telegram bot frontend and a REST API backend for recording and tracking family medical measurements (blood pressure, weight, temperature, etc.).

## 🏗️ Architecture

This project follows a **stateless microservices architecture**:

- **`telegram_bot/`** - Telegram bot frontend (stateless, communicates via REST API)
- **`health_svc/`** - FastAPI REST service for health data management (database layer)

The telegram bot is completely stateless and communicates with the health service via HTTP REST API calls.

## 📁 Project Structure

```
health-bot/
├── health_svc/              # Health Service API (Backend)
│   ├── api/                # FastAPI routes and schemas
│   ├── services/           # Business logic layer
│   ├── storage/            # Database layer (SQLite)
│   ├── tests/              # Unit tests
│   ├── main.py             # FastAPI application entry point
│   ├── migrate_db.py        # Database migration script
│   ├── requirements.txt    # Python dependencies
│   └── venv/               # Virtual environment (service-specific)
│
├── telegram_bot/            # Telegram Bot (Frontend)
│   ├── handlers/           # Bot command handlers
│   ├── clients/            # API client for health_svc
│   ├── tests/              # Unit tests
│   ├── bot.py              # Bot entry point
│   ├── requirements.txt    # Python dependencies
│   └── venv/               # Virtual environment (service-specific)
│
└── justfile                 # Task runner for monorepo management
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13+ (or compatible version)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- [just](https://github.com/casey/just) (optional but recommended) - Task runner for managing the monorepo
  - Install: `brew install just` (macOS) or see [installation guide](https://github.com/casey/just#installation)

### 1. Setup Project (Using Justfile - Recommended)

If you have `just` installed, you can use the justfile for easy project management:

```bash
# Complete setup: create venv, install dependencies, run migrations
just setup

# Check environment variables
just check-env
```

### 1. Setup Project (Manual)

Alternatively, set up manually:

```bash
# Create virtual environments for each service
python3 -m venv health_svc/venv
python3 -m venv telegram_bot/venv

# Install health service dependencies
cd health_svc
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..

# Install telegram bot dependencies
cd telegram_bot
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory or set environment variables:

```bash
# Required: Telegram Bot Token
export TELEGRAM_TOKEN="your_bot_token_here"

# Optional: Health Service API URL (default: http://localhost:8000)
export HEALTH_SVC_API_URL="http://localhost:8000"

# Optional: Health Service configuration
export HEALTH_SVC_HOST="0.0.0.0"
export HEALTH_SVC_PORT="8000"
export HEALTH_SVC_DB_DIR="data"
export HEALTH_SVC_DB_FILE="health_bot.db"
```

### 3. Initialize Database (Optional)

The database will be created automatically on first use, but you can run migrations manually:

**Using justfile:**
```bash
just migrate-status    # Check migration status
just migrate           # Run migration with backup
just migrate-dry-run   # Test migration without changes
```

**Manual:**
```bash
cd health_svc
python migrate_db.py --status
```

## 🧪 Running Tests

### Using Justfile (Recommended)

```bash
# Run all tests
just test

# Run tests for specific service
just test-api      # Health service tests
just test-bot      # Telegram bot tests

# Run tests with coverage
just test-coverage
just test-coverage-api
just test-coverage-bot

# Watch mode (auto-rerun on file changes)
just test-watch
```

### Manual Testing

Run tests for both modules:

```bash
# Run telegram_bot tests
cd telegram_bot
source venv/bin/activate
python -m pytest tests/ -v
deactivate
cd ..

# Run health_svc tests
cd health_svc
source venv/bin/activate
python -m pytest tests/ -v
deactivate
cd ..
```

### Run Tests from Root

You can also run tests individually from the root:

```bash
# Telegram bot tests
python -m pytest telegram_bot/tests/ -v

# Health service tests (must run from health_svc directory)
cd health_svc && python -m pytest tests/ -v && cd ..
```

## 🖥️ Running the Servers

### Using Justfile (Recommended)

The easiest way to manage all services:

```bash
# Start all services (API, Celery, Flower, Bot)
just

# Or start individually
just start-api      # Start FastAPI server
just start-celery   # Start Celery worker
just start-flower   # Start Flower (Celery monitoring)
just start-bot      # Start Telegram bot

# Check service status
just status

# Stop all services
just stop-all

# Restart all services
just restart

# View logs
just logs           # View recent logs
just logs-follow    # Follow logs in real-time

# Open API docs in browser
just docs

# Open Flower in browser
just flower-open
```

**Note**: Make sure Redis is running before starting Celery/Flower:
```bash
# Check Redis status
just check-redis

# Start Redis (if not running)
redis-server
```

### Manual Server Startup

#### Start Health Service API

The health service must be running before starting the telegram bot.

```bash
# Navigate to health_svc directory
cd health_svc

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the API server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base URL**: `http://localhost:8000`
- **Swagger UI (Interactive Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs) - Click-to-test interface

**💡 Tip:** Use the Swagger UI at `/docs` to interactively test all API endpoints directly from your browser!

#### Start Telegram Bot

In a **separate terminal**, start the telegram bot:

```bash
# Navigate to telegram_bot directory
cd telegram_bot

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the bot
python bot.py
```

**Note**: Make sure the health service is running before starting the bot, as the bot depends on the API.

## 📋 Available Commands

### Using Justfile

The project includes a comprehensive `justfile` for managing all aspects of the monorepo. Run `just --list` or `just help` to see all available commands.

#### Service Management
```bash
just                    # Start all services (default)
just start-api          # Start FastAPI server
just start-celery       # Start Celery worker
just start-flower       # Start Flower (Celery monitoring)
just start-bot          # Start Telegram bot
just stop-all           # Stop all services
just stop-api           # Stop FastAPI server
just stop-celery        # Stop Celery worker
just stop-flower        # Stop Flower
just stop-bot           # Stop Telegram bot
just status             # Check status of all services
just restart            # Restart all services
```

#### Dependency Management
```bash
just install            # Install all dependencies
just install-api        # Install health_svc dependencies
just install-bot        # Install telegram_bot dependencies
just update             # Update all dependencies
just update-api         # Update health_svc dependencies
just update-bot         # Update telegram_bot dependencies
```

#### Testing
```bash
just test               # Run all tests
just test-api           # Run health_svc tests
just test-bot           # Run telegram_bot tests
just test-coverage      # Run all tests with coverage
just test-coverage-api  # Run health_svc tests with coverage
just test-coverage-bot  # Run telegram_bot tests with coverage
just test-watch         # Run tests in watch mode
```

#### Development Utilities
```bash
just lint               # Run linters (ruff, pylint)
just format             # Format code (black, ruff)
just clean              # Clean Python cache files
just logs               # View service logs
just logs-follow        # Follow logs in real-time
```

#### Database Management
```bash
just migrate            # Run database migration with backup
just migrate-status     # Check migration status
just migrate-dry-run    # Test migration without changes
just db-reset           # Reset database (with confirmation)
```

#### Environment & Setup
```bash
just setup              # Complete project setup
just venv               # Create virtual environment
just check-env          # Check environment variables
just check-redis        # Check if Redis is running
```

#### Utilities
```bash
just help               # Show all available commands
just docs               # Open API docs in browser
just flower-open        # Open Flower in browser
```

### Manual Commands

#### Health Service

```bash
# Start API server
cd health_svc
source venv/bin/activate
python main.py

# Run database migration
python migrate_db.py --status          # Check migration status
python migrate_db.py --backup          # Run migration with backup
python migrate_db.py --dry-run         # Test migration without changes

# Run tests
python -m pytest tests/ -v
```

#### Telegram Bot

```bash
# Start bot
cd telegram_bot
source venv/bin/activate
python bot.py

# Run tests
python -m pytest tests/ -v
```

## 🔧 Configuration

### Health Service Configuration

Environment variables (with defaults):
- `HEALTH_SVC_HOST` - API host (default: `0.0.0.0`)
- `HEALTH_SVC_PORT` - API port (default: `8000`)
- `HEALTH_SVC_DB_DIR` - Database directory (default: `data`)
- `HEALTH_SVC_DB_FILE` - Database filename (default: `health_bot.db`)
- `HEALTH_SVC_RELOAD` - Enable auto-reload (default: `false`)
- `HEALTH_SVC_REDIS_URL` - Redis URL for Celery (default: `redis://localhost:6379`)

### Telegram Bot Configuration

Environment variables (with defaults):
- `TELEGRAM_TOKEN` - **Required** - Telegram bot token
- `HEALTH_SVC_API_URL` - Health service API URL (default: `http://localhost:8000`)

### Checking Configuration

Use the justfile to check your environment setup:

```bash
just check-env      # Check environment variables
just check-redis    # Check if Redis is running
```

## 📚 API Endpoints

The Health Service API provides the following endpoints:

### Health Check
- `GET /` - API information and version

### Patient Management
- `POST /api/v1/patients` - Create a new patient
  - Request: `{"name": "John Doe"}`
  - Returns: Patient object with ID and timestamp
  - Status: 201 Created (409 Conflict if patient exists)
- `GET /api/v1/patients` - Get all patients (sorted alphabetically)

### Health Records
- `POST /api/v1/records` - Create a new health record
  - Request: `{"timestamp": "2025-01-01T10:00:00", "patient": "John Doe", "record_type": "BP", "data_type": "text", "value": "120/80"}`
  - Returns: Created health record
  - Status: 201 Created (400 Bad Request if validation fails)
- `GET /api/v1/records` - Get health records with optional filters
  - Query params: `patient` (filter by name), `record_type` (filter by type), `limit` (max results, 1-1000)

### 📖 Interactive API Documentation

**Full interactive documentation is available when the service is running:**

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
  - Browse all endpoints organized by tags
  - Test endpoints directly with "Try it out" feature
  - View request/response schemas with examples
  - Validate requests before sending

For detailed API documentation and examples, see [`health_svc/README.md`](health_svc/README.md).

## 🧩 Telegram Bot Commands

- `/start` - Welcome message and help
- `/add_patient` - Add a new patient
- `/get_patients` - List all patients
- `/add_record` - Add a health record
- `/view_records` - View recent health records
- `/export` - Export records to CSV
- `/cancel` - Cancel current operation
- `/help` - Show available commands

## 🗄️ Database

The project uses SQLite for data storage. The database is automatically initialized on first use and includes:

- **`patients`** table - Patient information
- **`health_records`** table - Health measurement records

Database files are stored in:
- Health Service: `health_svc/data/health_bot.db`
- (Legacy) Telegram Bot: `telegram_bot/data/health_bot.db` (if exists)

## 🧪 Testing

The project includes comprehensive unit tests:

- **telegram_bot tests**: 21 tests covering handlers and API client
- **health_svc tests**: 11 tests covering database operations

All tests use pytest and can be run independently or together.

## 📖 Documentation

- `telegram_bot/README.md` - Telegram bot documentation
- `telegram_bot/MIGRATION_GUIDE.md` - Database migration guide
- `docs/ADR/` - Architecture Decision Records

## 🔒 Security Notes

- Never commit `.env` files or tokens to version control
- Use environment variables for sensitive configuration
- In production, restrict CORS origins in `health_svc/main.py`
- Consider using a more secure database backend for production

## 🛠️ Development

### Project Status

✅ **Completed**:
- Microservices architecture with stateless telegram bot
- REST API for health data management
- Database migration system
- Comprehensive test coverage
- API client for telegram bot

### Future Enhancements

- [ ] Add authentication/authorization
- [ ] Support for multiple database backends
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Production deployment guides

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📞 Support

[Add support/contact information here]

