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
│   └── requirements.txt    # Python dependencies
│
├── telegram_bot/            # Telegram Bot (Frontend)
│   ├── handlers/           # Bot command handlers
│   ├── clients/            # API client for health_svc
│   ├── tests/              # Unit tests
│   ├── bot.py              # Bot entry point
│   └── requirements.txt    # Python dependencies
│
└── venv/                   # Virtual environment (shared)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13+ (or compatible version)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### 1. Setup Virtual Environment

```bash
# Create virtual environment (if not already created)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install health service dependencies
cd health_svc
pip install -r requirements.txt

# Install telegram bot dependencies
cd ../telegram_bot
pip install -r requirements.txt

# Return to root
cd ..
```

### 3. Configure Environment Variables

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

### 4. Initialize Database (Optional)

The database will be created automatically on first use, but you can run migrations manually:

```bash
cd health_svc
python migrate_db.py --status
```

## 🧪 Running Tests

### Run All Tests

Run tests for both modules:

```bash
# Activate virtual environment
source venv/bin/activate

# Run telegram_bot tests
cd telegram_bot
python -m pytest tests/ -v

# Run health_svc tests
cd ../health_svc
python -m pytest tests/ -v
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

### Start Health Service API

The health service must be running before starting the telegram bot.

```bash
# Activate virtual environment
source venv/bin/activate

# Navigate to health_svc directory
cd health_svc

# Start the API server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base URL**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### Start Telegram Bot

In a **separate terminal**, start the telegram bot:

```bash
# Activate virtual environment
source venv/bin/activate

# Navigate to telegram_bot directory
cd telegram_bot

# Start the bot
python bot.py
```

**Note**: Make sure the health service is running before starting the bot, as the bot depends on the API.

## 📋 Available Commands

### Health Service

```bash
# Start API server
cd health_svc
python main.py

# Run database migration
python migrate_db.py --status          # Check migration status
python migrate_db.py --backup          # Run migration with backup
python migrate_db.py --dry-run         # Test migration without changes

# Run tests
python -m pytest tests/ -v
```

### Telegram Bot

```bash
# Start bot
cd telegram_bot
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

### Telegram Bot Configuration

Environment variables (with defaults):
- `TELEGRAM_TOKEN` - **Required** - Telegram bot token
- `HEALTH_SVC_API_URL` - Health service API URL (default: `http://localhost:8000`)

## 📚 API Endpoints

The Health Service API provides the following endpoints:

- `GET /` - API information
- `POST /api/v1/patients` - Create a new patient
- `GET /api/v1/patients` - Get all patients
- `POST /api/v1/records` - Create a new health record
- `GET /api/v1/records` - Get health records (with optional filters)

See `http://localhost:8000/docs` for full API documentation when the service is running.

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

