# Justfile for Health Bot Monorepo
# A comprehensive task runner for managing the health-bot Python monorepo

# ============================================================================
# VARIABLES
# ============================================================================

# Project directories
api_dir := "health_svc"
bot_dir := "telegram_bot"

# Python executable (use service-specific venv if available, otherwise system Python)
# Note: Each service has its own venv directory (health_svc/venv, telegram_bot/venv)

# Service ports
api_port := "8000"
flower_port := "5555"

# Redis configuration
redis_url := "redis://localhost:6379"

# Process ID files (for tracking running services)
pid_dir := ".pids"
api_pid := "{{pid_dir}}/api.pid"
celery_pid := "{{pid_dir}}/celery.pid"
flower_pid := "{{pid_dir}}/flower.pid"
bot_pid := "{{pid_dir}}/bot.pid"

# ============================================================================
# SERVICE MANAGEMENT
# ============================================================================

# Start all services (API, Celery, Flower, Bot)
default:
    @echo "Starting all services..."
    @just start-api
    @just start-celery
    @just start-flower
    @just start-bot
    @echo ""
    @echo "✅ All services started!"
    @echo "   API: http://localhost:{{api_port}}"
    @echo "   Flower: http://localhost:{{flower_port}}"
    @just status

# Start FastAPI server
start-api:
    #!/usr/bin/env bash
    set -e
    PID_DIR="{{pid_dir}}"
    API_PID="$PID_DIR/api.pid"
    mkdir -p "$PID_DIR"
    if [ -f "$API_PID" ]; then
        pid=$(cat "$API_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "⚠️  API server is already running (PID: $pid)"
            exit 0
        else
            rm -f "$API_PID"
        fi
    fi
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    echo "Starting FastAPI server..."
    cd {{api_dir}} && $PYTHON -m uvicorn main:app --host 0.0.0.0 --port {{api_port}} --reload > "../$PID_DIR/api.log" 2>&1 &
    echo $! > "$API_PID"
    sleep 2
    if [ -f "$API_PID" ] && ps -p $(cat "$API_PID") > /dev/null 2>&1; then
        echo "✅ FastAPI server started (PID: $(cat "$API_PID"))"
        echo "   API: http://localhost:{{api_port}}"
        echo "   Docs: http://localhost:{{api_port}}/docs"
    else
        echo "❌ Failed to start FastAPI server. Check logs: $PID_DIR/api.log"
        exit 1
    fi

# Start Celery worker
start-celery:
    #!/usr/bin/env bash
    set -e
    PID_DIR="{{pid_dir}}"
    CELERY_PID="$PID_DIR/celery.pid"
    mkdir -p "$PID_DIR"
    if [ -f "$CELERY_PID" ]; then
        pid=$(cat "$CELERY_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "⚠️  Celery worker is already running (PID: $pid)"
            exit 0
        else
            rm -f "$CELERY_PID"
        fi
    fi
    if ! command -v redis-cli &> /dev/null; then
        echo "⚠️  redis-cli not found. Please install Redis."
        exit 1
    fi
    if ! redis-cli -u {{redis_url}} ping > /dev/null 2>&1; then
        echo "❌ Redis is not running at {{redis_url}}"
        echo "   Please start Redis: redis-server"
        exit 1
    fi
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    echo "Starting Celery worker..."
    cd {{api_dir}} && $PYTHON -m celery -A celery_app worker --loglevel=info > "../$PID_DIR/celery.log" 2>&1 &
    echo $! > "$CELERY_PID"
    sleep 2
    if [ -f "$CELERY_PID" ] && ps -p $(cat "$CELERY_PID") > /dev/null 2>&1; then
        echo "✅ Celery worker started (PID: $(cat "$CELERY_PID"))"
    else
        echo "❌ Failed to start Celery worker. Check logs: $PID_DIR/celery.log"
        exit 1
    fi

# Start Flower (Celery monitoring)
start-flower:
    #!/usr/bin/env bash
    set -e
    PID_DIR="{{pid_dir}}"
    FLOWER_PID="$PID_DIR/flower.pid"
    mkdir -p "$PID_DIR"
    if [ -f "$FLOWER_PID" ]; then
        pid=$(cat "$FLOWER_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "⚠️  Flower is already running (PID: $pid)"
            exit 0
        else
            rm -f "$FLOWER_PID"
        fi
    fi
    if ! command -v redis-cli &> /dev/null; then
        echo "⚠️  redis-cli not found. Please install Redis."
        exit 1
    fi
    if ! redis-cli -u {{redis_url}} ping > /dev/null 2>&1; then
        echo "❌ Redis is not running at {{redis_url}}"
        echo "   Please start Redis: redis-server"
        exit 1
    fi
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    echo "Starting Flower..."
    cd {{api_dir}} && $PYTHON -m celery -A celery_app flower --port={{flower_port}} > "../$PID_DIR/flower.log" 2>&1 &
    echo $! > "$FLOWER_PID"
    sleep 2
    if [ -f "$FLOWER_PID" ] && ps -p $(cat "$FLOWER_PID") > /dev/null 2>&1; then
        echo "✅ Flower started (PID: $(cat "$FLOWER_PID"))"
        echo "   Flower: http://localhost:{{flower_port}}"
    else
        echo "❌ Failed to start Flower. Check logs: $PID_DIR/flower.log"
        exit 1
    fi

# Start Telegram bot
start-bot:
    #!/usr/bin/env bash
    set -e
    PID_DIR="{{pid_dir}}"
    BOT_PID="$PID_DIR/bot.pid"
    mkdir -p "$PID_DIR"
    if [ -f "$BOT_PID" ]; then
        pid=$(cat "$BOT_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "⚠️  Telegram bot is already running (PID: $pid)"
            exit 0
        else
            rm -f "$BOT_PID"
        fi
    fi
    if [ -d "{{bot_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{bot_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    echo "Starting Telegram bot..."
    cd {{bot_dir}} && $PYTHON bot.py > "../$PID_DIR/bot.log" 2>&1 &
    echo $! > "$BOT_PID"
    sleep 2
    if [ -f "$BOT_PID" ] && ps -p $(cat "$BOT_PID") > /dev/null 2>&1; then
        echo "✅ Telegram bot started (PID: $(cat "$BOT_PID"))"
    else
        echo "❌ Failed to start Telegram bot. Check logs: $PID_DIR/bot.log"
        exit 1
    fi

# Stop all services
stop-all:
    @echo "Stopping all services..."
    @just stop-api
    @just stop-celery
    @just stop-flower
    @just stop-bot
    @echo "✅ All services stopped"

# Stop FastAPI server
stop-api:
    #!/usr/bin/env bash
    PID_DIR="{{pid_dir}}"
    API_PID="$PID_DIR/api.pid"
    if [ -f "$API_PID" ]; then
        pid=$(cat "$API_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping FastAPI server (PID: $pid)..."
            kill $pid 2>/dev/null || true
            sleep 1
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi
        rm -f "$API_PID"
        echo "✅ FastAPI server stopped"
    else
        echo "ℹ️  FastAPI server is not running"
    fi

# Stop Celery worker
stop-celery:
    #!/usr/bin/env bash
    PID_DIR="{{pid_dir}}"
    CELERY_PID="$PID_DIR/celery.pid"
    if [ -f "$CELERY_PID" ]; then
        pid=$(cat "$CELERY_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping Celery worker (PID: $pid)..."
            kill $pid 2>/dev/null || true
            sleep 1
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi
        rm -f "$CELERY_PID"
        echo "✅ Celery worker stopped"
    else
        echo "ℹ️  Celery worker is not running"
    fi

# Stop Flower
stop-flower:
    #!/usr/bin/env bash
    PID_DIR="{{pid_dir}}"
    FLOWER_PID="$PID_DIR/flower.pid"
    if [ -f "$FLOWER_PID" ]; then
        pid=$(cat "$FLOWER_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping Flower (PID: $pid)..."
            kill $pid 2>/dev/null || true
            sleep 1
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi
        rm -f "$FLOWER_PID"
        echo "✅ Flower stopped"
    else
        echo "ℹ️  Flower is not running"
    fi

# Stop Telegram bot
stop-bot:
    #!/usr/bin/env bash
    PID_DIR="{{pid_dir}}"
    BOT_PID="$PID_DIR/bot.pid"
    if [ -f "$BOT_PID" ]; then
        pid=$(cat "$BOT_PID")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping Telegram bot (PID: $pid)..."
            kill $pid 2>/dev/null || true
            sleep 1
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi
        rm -f "$BOT_PID"
        echo "✅ Telegram bot stopped"
    else
        echo "ℹ️  Telegram bot is not running"
    fi

# Show status of all services
status:
    @echo "Service Status:"
    @echo "==============="
    @if [ -f {{api_pid}} ] && ps -p $(cat {{api_pid}}) > /dev/null 2>&1; then \
        echo "✅ API: Running (PID: $(cat {{api_pid}}))"; \
    else \
        echo "❌ API: Not running"; \
    fi
    @if [ -f {{celery_pid}} ] && ps -p $(cat {{celery_pid}}) > /dev/null 2>&1; then \
        echo "✅ Celery: Running (PID: $(cat {{celery_pid}}))"; \
    else \
        echo "❌ Celery: Not running"; \
    fi
    @if [ -f {{flower_pid}} ] && ps -p $(cat {{flower_pid}}) > /dev/null 2>&1; then \
        echo "✅ Flower: Running (PID: $(cat {{flower_pid}}))"; \
    else \
        echo "❌ Flower: Not running"; \
    fi
    @if [ -f {{bot_pid}} ] && ps -p $(cat {{bot_pid}}) > /dev/null 2>&1; then \
        echo "✅ Bot: Running (PID: $(cat {{bot_pid}}))"; \
    else \
        echo "❌ Bot: Not running"; \
    fi
    @echo ""
    @if command -v redis-cli &> /dev/null && redis-cli -u {{redis_url}} ping > /dev/null 2>&1; then \
        echo "✅ Redis: Running"; \
    else \
        echo "❌ Redis: Not running"; \
    fi

# Restart all services
restart:
    @just stop-all
    @sleep 2
    @just default

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

# Install dependencies for all services
install:
    @echo "Installing dependencies for all services..."
    @just install-api
    @just install-bot
    @echo "✅ All dependencies installed"

# Install health_svc dependencies
install-api:
    #!/usr/bin/env bash
    echo "Installing health_svc dependencies..."
    if [ -d "{{api_dir}}/venv" ]; then
        PIP="$(pwd)/{{api_dir}}/venv/bin/pip"
    else
        PIP="pip3"
    fi
    cd {{api_dir}} && $PIP install -r requirements.txt
    echo "✅ health_svc dependencies installed"

# Install telegram_bot dependencies
install-bot:
    #!/usr/bin/env bash
    echo "Installing telegram_bot dependencies..."
    if [ -d "{{bot_dir}}/venv" ]; then
        PIP="$(pwd)/{{bot_dir}}/venv/bin/pip"
    else
        PIP="pip3"
    fi
    cd {{bot_dir}} && $PIP install -r requirements.txt
    echo "✅ telegram_bot dependencies installed"

# Update all dependencies
update:
    @echo "Updating dependencies for all services..."
    @just update-api
    @just update-bot
    @echo "✅ All dependencies updated"

# Update health_svc dependencies
update-api:
    #!/usr/bin/env bash
    echo "Updating health_svc dependencies..."
    if [ -d "{{api_dir}}/venv" ]; then
        PIP="$(pwd)/{{api_dir}}/venv/bin/pip"
    else
        PIP="pip3"
    fi
    cd {{api_dir}} && $PIP install --upgrade -r requirements.txt
    echo "✅ health_svc dependencies updated"

# Update telegram_bot dependencies
update-bot:
    #!/usr/bin/env bash
    echo "Updating telegram_bot dependencies..."
    if [ -d "{{bot_dir}}/venv" ]; then
        PIP="$(pwd)/{{bot_dir}}/venv/bin/pip"
    else
        PIP="pip3"
    fi
    cd {{bot_dir}} && $PIP install --upgrade -r requirements.txt
    echo "✅ telegram_bot dependencies updated"

# ============================================================================
# TESTING
# ============================================================================

# Run all tests
test:
    @echo "Running all tests..."
    @just test-api
    @just test-bot
    @echo "✅ All tests completed"

# Run health_svc tests
test-api:
    #!/usr/bin/env bash
    echo "Running health_svc tests..."
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{api_dir}} && $PYTHON -m pytest tests/ -v
    echo "✅ health_svc tests completed"

# Run telegram_bot tests
test-bot:
    #!/usr/bin/env bash
    echo "Running telegram_bot tests..."
    if [ -d "{{bot_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{bot_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{bot_dir}} && $PYTHON -m pytest tests/ -v
    echo "✅ telegram_bot tests completed"

# Run tests with coverage
test-coverage:
    @echo "Running all tests with coverage..."
    @just test-coverage-api
    @just test-coverage-bot
    @echo "✅ Coverage reports generated"

# Run health_svc tests with coverage
test-coverage-api:
    #!/usr/bin/env bash
    echo "Running health_svc tests with coverage..."
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{api_dir}} && $PYTHON -m pytest tests/ --cov=. --cov-report=html --cov-report=term
    echo "✅ Coverage report: {{api_dir}}/htmlcov/index.html"

# Run telegram_bot tests with coverage
test-coverage-bot:
    #!/usr/bin/env bash
    echo "Running telegram_bot tests with coverage..."
    if [ -d "{{bot_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{bot_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{bot_dir}} && $PYTHON -m pytest tests/ --cov=. --cov-report=html --cov-report=term
    echo "✅ Coverage report: {{bot_dir}}/htmlcov/index.html"

# Run tests in watch mode (requires pytest-watch)
test-watch:
    #!/usr/bin/env bash
    echo "Running tests in watch mode..."
    if [ -d "{{api_dir}}/venv" ]; then
        API_PIP="$(pwd)/{{api_dir}}/venv/bin/pip"
        API_PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        API_PIP="pip3"
        API_PYTHON="python3"
    fi
    if [ -d "{{bot_dir}}/venv" ]; then
        BOT_PIP="$(pwd)/{{bot_dir}}/venv/bin/pip"
        BOT_PYTHON="$(pwd)/{{bot_dir}}/venv/bin/python"
    else
        BOT_PIP="pip3"
        BOT_PYTHON="python3"
    fi
    if ! $API_PIP show pytest-watch > /dev/null 2>&1; then
        echo "Installing pytest-watch in health_svc..."
        $API_PIP install pytest-watch
    fi
    if ! $BOT_PIP show pytest-watch > /dev/null 2>&1; then
        echo "Installing pytest-watch in telegram_bot..."
        $BOT_PIP install pytest-watch
    fi
    echo "Watching for changes. Press Ctrl+C to stop."
    cd {{api_dir}} && $API_PYTHON -m ptw tests/ -- -v &
    cd {{bot_dir}} && $BOT_PYTHON -m ptw tests/ -- -v &
    wait

# ============================================================================
# DEVELOPMENT UTILITIES
# ============================================================================

# Generate health graph preview HTML for UX review
preview-graph:
    #!/usr/bin/env bash
    echo "Generating health graph preview..."
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{api_dir}} && $PYTHON preview_graph.py
    echo ""
    echo "Opening preview in browser..."
    if command -v open &> /dev/null; then
        open ../health_graph_preview.html
    elif command -v xdg-open &> /dev/null; then
        xdg-open ../health_graph_preview.html
    else
        echo "Please open: health_graph_preview.html"
    fi

# Run linting on all services
lint:
    #!/usr/bin/env bash
    echo "Running linters..."
    # Try to find ruff in PATH or service venvs
    RUFF_CMD=""
    if command -v ruff &> /dev/null; then
        RUFF_CMD="ruff"
    elif [ -f "{{api_dir}}/venv/bin/ruff" ]; then
        RUFF_CMD="$(pwd)/{{api_dir}}/venv/bin/ruff"
    elif [ -f "{{bot_dir}}/venv/bin/ruff" ]; then
        RUFF_CMD="$(pwd)/{{bot_dir}}/venv/bin/ruff"
    fi
    if [ -n "$RUFF_CMD" ]; then
        echo "Linting health_svc..."
        cd {{api_dir}} && $RUFF_CMD check . || true
        echo "Linting telegram_bot..."
        cd {{bot_dir}} && $RUFF_CMD check . || true
    else
        echo "⚠️  ruff not found. Install with: pip install ruff (in either service venv or system)"
    fi
    # Try to find pylint in PATH or service venvs
    PYLINT_CMD=""
    if command -v pylint &> /dev/null; then
        PYLINT_CMD="pylint"
    elif [ -f "{{api_dir}}/venv/bin/pylint" ]; then
        PYLINT_CMD="$(pwd)/{{api_dir}}/venv/bin/pylint"
    elif [ -f "{{bot_dir}}/venv/bin/pylint" ]; then
        PYLINT_CMD="$(pwd)/{{bot_dir}}/venv/bin/pylint"
    fi
    if [ -n "$PYLINT_CMD" ]; then
        echo "Running pylint on health_svc..."
        cd {{api_dir}} && $PYLINT_CMD **/*.py --ignore=tests || true
        echo "Running pylint on telegram_bot..."
        cd {{bot_dir}} && $PYLINT_CMD **/*.py --ignore=tests || true
    fi
    echo "✅ Linting completed"

# Format code in all services
format:
    #!/usr/bin/env bash
    echo "Formatting code..."
    # Try to find black in PATH or service venvs
    BLACK_CMD=""
    if command -v black &> /dev/null; then
        BLACK_CMD="black"
    elif [ -f "{{api_dir}}/venv/bin/black" ]; then
        BLACK_CMD="$(pwd)/{{api_dir}}/venv/bin/black"
    elif [ -f "{{bot_dir}}/venv/bin/black" ]; then
        BLACK_CMD="$(pwd)/{{bot_dir}}/venv/bin/black"
    fi
    if [ -n "$BLACK_CMD" ]; then
        echo "Formatting health_svc..."
        cd {{api_dir}} && $BLACK_CMD . || true
        echo "Formatting telegram_bot..."
        cd {{bot_dir}} && $BLACK_CMD . || true
    else
        echo "⚠️  black not found. Install with: pip install black (in either service venv or system)"
    fi
    # Try to find ruff in PATH or service venvs
    RUFF_CMD=""
    if command -v ruff &> /dev/null; then
        RUFF_CMD="ruff"
    elif [ -f "{{api_dir}}/venv/bin/ruff" ]; then
        RUFF_CMD="$(pwd)/{{api_dir}}/venv/bin/ruff"
    elif [ -f "{{bot_dir}}/venv/bin/ruff" ]; then
        RUFF_CMD="$(pwd)/{{bot_dir}}/venv/bin/ruff"
    fi
    if [ -n "$RUFF_CMD" ]; then
        echo "Formatting with ruff..."
        cd {{api_dir}} && $RUFF_CMD format . || true
        cd {{bot_dir}} && $RUFF_CMD format . || true
    fi
    echo "✅ Code formatted"

# Clean Python cache files
clean:
    @echo "Cleaning Python cache files..."
    @find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    @find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @find . -type f -name "*.pyo" -delete 2>/dev/null || true
    @find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
    @find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
    @find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
    @find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
    @find . -type f -name ".coverage" -delete 2>/dev/null || true
    @echo "✅ Cache files cleaned"

# View logs from all services
logs:
    @echo "Service Logs:"
    @echo "============="
    @if [ -f {{pid_dir}}/api.log ]; then \
        echo "\n--- API Log ---"; \
        tail -n 20 {{pid_dir}}/api.log; \
    fi
    @if [ -f {{pid_dir}}/celery.log ]; then \
        echo "\n--- Celery Log ---"; \
        tail -n 20 {{pid_dir}}/celery.log; \
    fi
    @if [ -f {{pid_dir}}/flower.log ]; then \
        echo "\n--- Flower Log ---"; \
        tail -n 20 {{pid_dir}}/flower.log; \
    fi
    @if [ -f {{pid_dir}}/bot.log ]; then \
        echo "\n--- Bot Log ---"; \
        tail -n 20 {{pid_dir}}/bot.log; \
    fi

# Follow logs (tail -f)
logs-follow:
    @echo "Following service logs (Ctrl+C to stop)..."
    @tail -f {{pid_dir}}/*.log 2>/dev/null || echo "No log files found"

# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================

# Run database migration
migrate:
    #!/usr/bin/env bash
    echo "Running database migration..."
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{api_dir}} && $PYTHON migrate_db.py --backup
    echo "✅ Migration completed"

# Check migration status
migrate-status:
    #!/usr/bin/env bash
    echo "Checking migration status..."
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{api_dir}} && $PYTHON migrate_db.py --status

# Dry run migration (no changes)
migrate-dry-run:
    #!/usr/bin/env bash
    echo "Running migration dry-run..."
    if [ -d "{{api_dir}}/venv" ]; then
        PYTHON="$(pwd)/{{api_dir}}/venv/bin/python"
    else
        PYTHON="python3"
    fi
    cd {{api_dir}} && $PYTHON migrate_db.py --dry-run

# Reset database (with confirmation)
db-reset:
    #!/usr/bin/env bash
    echo "⚠️  WARNING: This will delete all database data!"
    read -p "Are you sure? Type 'yes' to confirm: " confirm
    if [ "$confirm" = "yes" ]; then
        echo "Resetting database..."
        cd {{api_dir}} && rm -f data/health_bot.db*
        echo "✅ Database reset. Run 'just migrate' to initialize."
    else
        echo "❌ Database reset cancelled"
    fi

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

# Initial project setup
setup:
    @echo "Setting up Health Bot project..."
    @just venv
    @just install
    @just migrate
    @echo ""
    @echo "✅ Project setup complete!"
    @echo ""
    @just check-env

# Create virtual environments for all services
venv:
    @echo "Creating virtual environments..."
    @if [ -d "{{api_dir}}/venv" ]; then \
        echo "⚠️  {{api_dir}}/venv already exists"; \
    else \
        echo "Creating {{api_dir}}/venv..."; \
        python3 -m venv {{api_dir}}/venv; \
        echo "✅ {{api_dir}}/venv created"; \
    fi
    @if [ -d "{{bot_dir}}/venv" ]; then \
        echo "⚠️  {{bot_dir}}/venv already exists"; \
    else \
        echo "Creating {{bot_dir}}/venv..."; \
        python3 -m venv {{bot_dir}}/venv; \
        echo "✅ {{bot_dir}}/venv created"; \
    fi
    @echo ""
    @echo "✅ Virtual environments created!"
    @echo "   Activate health_svc venv: source {{api_dir}}/venv/bin/activate"
    @echo "   Activate telegram_bot venv: source {{bot_dir}}/venv/bin/activate"

# Check required environment variables
check-env:
    #!/usr/bin/env bash
    echo "Checking environment variables..."
    echo "================================"
    if [ -z "$TELEGRAM_TOKEN" ]; then
        echo "❌ TELEGRAM_TOKEN: Not set"
    else
        echo "✅ TELEGRAM_TOKEN: Set"
    fi
    if [ -z "$HEALTH_SVC_REDIS_URL" ]; then
        echo "ℹ️  HEALTH_SVC_REDIS_URL: Using default ({{redis_url}})"
    else
        echo "✅ HEALTH_SVC_REDIS_URL: $HEALTH_SVC_REDIS_URL"
    fi
    if [ -z "$HEALTH_SVC_HOST" ]; then
        echo "ℹ️  HEALTH_SVC_HOST: Using default (0.0.0.0)"
    else
        echo "✅ HEALTH_SVC_HOST: $HEALTH_SVC_HOST"
    fi
    if [ -z "$HEALTH_SVC_PORT" ]; then
        echo "ℹ️  HEALTH_SVC_PORT: Using default ({{api_port}})"
    else
        echo "✅ HEALTH_SVC_PORT: $HEALTH_SVC_PORT"
    fi
    echo ""
    echo "Note: Set environment variables in .env file or export them"

# ============================================================================
# UTILITY COMMANDS
# ============================================================================

# Show help/available commands
help:
    @just --list

# Check if Redis is running
check-redis:
    #!/usr/bin/env bash
    if ! command -v redis-cli &> /dev/null; then
        echo "⚠️  redis-cli not found. Please install Redis."
        exit 1
    fi
    if ! redis-cli -u {{redis_url}} ping > /dev/null 2>&1; then
        echo "❌ Redis is not running at {{redis_url}}"
        echo "   Please start Redis: redis-server"
        exit 1
    fi
    echo "✅ Redis is running at {{redis_url}}"

# Open API documentation in browser
docs:
    @echo "Opening API documentation..."
    @if command -v open &> /dev/null; then \
        open http://localhost:{{api_port}}/docs; \
    elif command -v xdg-open &> /dev/null; then \
        xdg-open http://localhost:{{api_port}}/docs; \
    else \
        echo "Please open: http://localhost:{{api_port}}/docs"; \
    fi

# Open Flower in browser
flower-open:
    @echo "Opening Flower..."
    @if command -v open &> /dev/null; then \
        open http://localhost:{{flower_port}}; \
    elif command -v xdg-open &> /dev/null; then \
        xdg-open http://localhost:{{flower_port}}; \
    else \
        echo "Please open: http://localhost:{{flower_port}}"; \
    fi
