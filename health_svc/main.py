"""
FastAPI application entry point for Health Service API.

This module configures and creates the FastAPI application with:
- Dependency Injection: Services and repositories injected via Depends()
- Exception Handling: Consistent error responses via setup_exception_handlers()
- CORS Middleware: Allows cross-origin requests from telegram_bot
- Lifespan Management: Database initialization and cleanup

Architecture Overview:
    ┌─────────────────────────────────────────────────────────────┐
    │                     FastAPI Application                      │
    ├─────────────────────────────────────────────────────────────┤
    │  Routers (api/routers/)                                     │
    │    ├── health.py     - Health check endpoints               │
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
from api.routers import health_router, patients_router, records_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the application.
    This replaces the deprecated @app.on_event("startup") pattern.
    
    Startup:
        - Initializes database connection (triggers schema creation)
        - Logs configuration for debugging
    
    Shutdown:
        - Logs shutdown message
        - Resources are cleaned up by Python GC
    """
    # Startup: Initialize database via DI
    # This ensures the database is ready before any requests
    logger.info("Starting Health Service API...")
    db = get_database()
    logger.info(f"Database initialized: {db.db_path}")
    
    yield  # Application runs here
    
    # Shutdown: Cleanup resources if needed
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
# Configure CORS to allow telegram_bot to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# ROUTERS
# =============================================================================
# Include routers - each router uses Depends() for service injection
app.include_router(health_router)
app.include_router(patients_router)
app.include_router(records_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
