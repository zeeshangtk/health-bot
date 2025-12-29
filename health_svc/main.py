"""
FastAPI application entry point for Health Service API.

This module configures and creates the FastAPI application with:
- Structured JSON Logging: Request/response logging for Grafana/Loki
- Request ID Propagation: UUID-based request tracking across logs
- Dependency Injection: Services and repositories injected via Depends()
- Exception Handling: Consistent error responses via setup_exception_handlers()
- CORS Middleware: Allows cross-origin requests from telegram_bot
- Lifespan Management: Database initialization and cleanup
- Metrics Collection: In-memory metrics for Prometheus/Grafana scraping

Architecture Overview:
    ┌─────────────────────────────────────────────────────────────┐
    │                     FastAPI Application                      │
    ├─────────────────────────────────────────────────────────────┤
    │  Middleware Stack (order matters!)                          │
    │    ├── LoggingMiddleware  - Request logging & metrics       │
    │    └── CORSMiddleware     - Cross-origin support            │
    ├─────────────────────────────────────────────────────────────┤
    │  Routers (api/routers/)                                     │
    │    ├── health.py     - /health, /ready, /metrics endpoints  │
    │    ├── patients.py   - Patient CRUD                         │
    │    └── records.py    - Health records & uploads             │
    ├─────────────────────────────────────────────────────────────┤
    │  Services (services/)     ← Injected via Depends()          │
    │    ├── PatientService     - Patient business logic          │
    │    ├── HealthService      - Record business logic           │
    │    ├── UploadService      - File upload handling            │
    │    └── GraphService       - Visualization generation        │
    ├─────────────────────────────────────────────────────────────┤
    │  Repositories (repositories/)   ← Injected into Services    │
    │    ├── PatientRepository        - Patient data access       │
    │    └── HealthRecordRepository   - Record data access        │
    ├─────────────────────────────────────────────────────────────┤
    │  Database (SQLite)              ← Injected into Repositories│
    └─────────────────────────────────────────────────────────────┘

Observability Features:
    - Structured JSON logs for Grafana Loki
    - Request ID in logs and X-Request-ID response header
    - /health endpoint for liveness probes
    - /ready endpoint for readiness probes (checks DB, Redis)
    - /metrics endpoint for Prometheus scraping

Dependency Injection Flow:
    1. Request arrives at router endpoint
    2. FastAPI resolves Depends(get_*_service) dependencies
    3. Dependency functions (core/dependencies.py) create service instances
    4. Services receive repository instances via their constructors
    5. Repositories receive database instance via their constructors
    6. Handler executes with fully configured dependency graph
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import API_HOST, API_PORT, API_RELOAD
from core.dependencies import get_database
from core.exceptions import setup_exception_handlers
from core.logging_config import setup_logging
from core.middleware import LoggingMiddleware
from api.routers import health_router, patients_router, records_router, meta_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the application.
    This replaces the deprecated @app.on_event("startup") pattern.
    
    Startup:
        - Configures structured JSON logging
        - Initializes database connection (triggers schema creation)
        - Logs configuration for debugging
    
    Shutdown:
        - Logs shutdown message
        - Resources are cleaned up by Python GC
    """
    # =========================================================================
    # STARTUP
    # =========================================================================
    
    # Configure structured logging FIRST (before any other logging)
    # This ensures all startup logs are properly formatted
    setup_logging(level="INFO", json_format=True)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Health Service API...")
    
    # Initialize database via DI
    # This ensures the database is ready before any requests
    db = get_database()
    logger.info(
        "Database initialized",
        extra={"db_path": db.db_path}
    )
    
    yield  # Application runs here
    
    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    logger.info("Health Service API shutting down...")


# Create FastAPI app with lifespan context
app = FastAPI(
    title="Health Service API",
    description="REST API for health record management. Track and manage patient health records including blood pressure, weight, temperature, and other measurements.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================
# Register custom exception handlers for consistent error responses.
# HealthServiceError and its subclasses are converted to appropriate HTTP responses.
setup_exception_handlers(app)

# =============================================================================
# MIDDLEWARE
# =============================================================================
# Order matters! Middleware is executed in REVERSE order of registration.
# Last registered = first to handle request, last to handle response.

# 1. CORS Middleware (innermost - closest to routes)
# Configure CORS to allow telegram_bot to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Logging Middleware (outermost - captures all requests)
# Generates request_id, logs requests, collects metrics
app.add_middleware(LoggingMiddleware)

# =============================================================================
# ROUTERS
# =============================================================================
# Include routers - each router uses Depends() for service injection
app.include_router(health_router)
app.include_router(patients_router)
app.include_router(records_router)
app.include_router(meta_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
