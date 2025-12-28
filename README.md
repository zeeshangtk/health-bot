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
│   ├── api/                # FastAPI routes
│   │   └── routers/        # API endpoint routers
│   ├── core/               # Core configuration
│   ├── models/             # Domain models
│   ├── repositories/       # Database access layer
│   ├── schemas/            # Pydantic schemas for API validation
│   ├── services/           # Business logic layer
│   ├── tasks/              # Celery background tasks
│   ├── tests/              # Unit tests
│   ├── main.py             # FastAPI application entry point
│   ├── migrate_db.py       # Database migration script
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

## 🐳 Docker Deployment

This project is fully containerized with multi-architecture support (linux/amd64 and linux/arm64) for deployment on both standard servers and Raspberry Pi devices.

### Architecture

The Docker setup includes:
- **health_svc**: FastAPI REST API service
- **telegram_bot**: Telegram bot service
- **redis**: Redis server for Celery task queue
- **celery_worker**: Background task processor
- **flower**: Celery monitoring dashboard (optional)

### Prerequisites

- Docker Engine 20.10+ with Buildx support
- Docker Compose 2.0+
- GitHub Container Registry (GHCR) access (for pulling images)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Building Images Locally

You can build images locally for testing:

```bash
# Build health_svc image
docker buildx build --platform linux/amd64,linux/arm64 \
  -t health_svc:latest \
  -f health_svc/Dockerfile \
  health_svc/

# Build telegram_bot image
docker buildx build --platform linux/amd64,linux/arm64 \
  -t telegram_bot:latest \
  -f telegram_bot/Dockerfile \
  telegram_bot/
```

### CI/CD Pipeline (GitHub Actions)

The project includes a GitHub Actions workflow (`.github/workflows/build.yml`) that automatically:

1. **Builds multi-arch images** (linux/amd64, linux/arm64) using Docker Buildx
2. **Pushes to GHCR** with proper tagging
3. **Caches layers** for faster builds
4. **Triggers on**:
   - Push to `master`/`main` branch
   - Pull requests (build only, no push)
   - Manual workflow dispatch

#### Setting Up GitHub Actions

1. **No additional secrets required** - The workflow uses `GITHUB_TOKEN` automatically provided by GitHub Actions
2. **Image naming**: Images are pushed as:
   - `ghcr.io/<your-username>/health_svc:<tag>`
   - `ghcr.io/<your-username>/telegram_bot:<tag>`
3. **Tags**: Uses `latest` by default, or custom tag via workflow dispatch

#### Manual Workflow Trigger

You can manually trigger builds via GitHub Actions UI:
- Go to Actions → Build and Push Docker Images → Run workflow
- Select service (all, health_svc, or telegram_bot)
- Optionally specify a custom tag

### Deploying on Raspberry Pi

#### 1. Prepare Environment File

Create a `.env` file in the project root (NEVER commit this file):

```bash
# Docker Registry Configuration
REGISTRY=ghcr.io
GITHUB_REPO_OWNER=your-username

# Image tags
HEALTH_SVC_TAG=latest
TELEGRAM_BOT_TAG=latest

# Service ports
HEALTH_SVC_PORT=8000
FLOWER_PORT=5555

# REQUIRED: Telegram Bot Token
TELEGRAM_TOKEN=your_telegram_bot_token_here
```

**⚠️ Security Best Practices:**
- ✅ Store `.env` file on Raspberry Pi only
- ✅ Use GitHub Actions Secrets for CI/CD (not needed for this workflow)
- ✅ Never commit `.env` files to git
- ✅ Use `.env.example` as a template (without secrets)
- ❌ Never hard-code secrets in Dockerfiles
- ❌ Never commit tokens or passwords

#### 2. Authenticate with GHCR

On your Raspberry Pi, authenticate with GitHub Container Registry:

```bash
# Login to GHCR (requires GitHub Personal Access Token with read:packages permission)
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Or use interactive login
docker login ghcr.io
```

**Creating a GitHub Personal Access Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `read:packages` scope
3. Use this token for Docker login

#### 3. Pull Images

Pull the latest images from GHCR:

```bash
# Pull all service images
docker compose pull

# Or pull individually
docker pull ghcr.io/your-username/health_svc:latest
docker pull ghcr.io/your-username/telegram_bot:latest
```

#### 4. Start Services

Start all services with Docker Compose:

```bash
# Start all services in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Check service status
docker compose ps

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

#### 5. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/

# View API documentation
# Open http://localhost:8000/docs in browser

# Check Flower dashboard
# Open http://localhost:5555 in browser

# View service logs
docker compose logs health_svc
docker compose logs telegram_bot
docker compose logs celery_worker
```

### Docker Compose Configuration

The `docker-compose.yml` file includes:

- **Multi-service orchestration**: All services in a single network
- **Volume persistence**: Database and uploads stored in named volumes
- **Health checks**: Automatic service health monitoring
- **Dependency management**: Services start in correct order
- **Restart policies**: Automatic restart on failure

#### Service Ports

- **Health Service API**: `8000` (configurable via `HEALTH_SVC_PORT`)
- **Flower Dashboard**: `5555` (configurable via `FLOWER_PORT`)
- **Redis**: `6379` (internal only, not exposed)

#### Data Persistence

Data is stored in Docker volumes:
- `redis_data`: Redis persistence
- `health_svc_data`: SQLite database
- `health_svc_uploads`: Uploaded files

To backup data:
```bash
# Backup volumes
docker run --rm -v health-bot_health_svc_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/health_svc_data_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v health-bot_health_svc_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/health_svc_data_backup.tar.gz -C /data
```

### Updating Services

To update to the latest images:

```bash
# Pull latest images
docker compose pull

# Restart services with new images
docker compose up -d

# Or force recreate
docker compose up -d --force-recreate
```

### Troubleshooting

#### Images not found
- Verify GHCR authentication: `docker login ghcr.io`
- Check image name matches your GitHub username
- Ensure images were built and pushed successfully

#### Services not starting
- Check logs: `docker compose logs <service-name>`
- Verify `.env` file exists and contains required variables
- Check port conflicts: `netstat -tulpn | grep <port>`

#### Database issues
- Check volume permissions: `docker volume inspect health-bot_health_svc_data`
- Verify database directory is writable

#### Network connectivity
- Services communicate via `health-bot-network` Docker network
- Use service names as hostnames (e.g., `http://health_svc:8000`)

### Development with Docker

For local development, you can mount source code as volumes:

```yaml
# Add to docker-compose.yml services (development only)
volumes:
  - ./health_svc:/app
  - ./telegram_bot:/app
```

**⚠️ Warning**: This is for development only. Production should use built images.

## 🖥️ Running the Servers (Local Development)

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
- [ ] Production deployment guides (Kubernetes, etc.)
- [ ] Monitoring and observability (Prometheus, Grafana)
- [ ] Automated database backups

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📞 Support

[Add support/contact information here]

