"""
FastAPI application entry point for Health Service API.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import API_HOST, API_PORT, API_RELOAD
from api.routers import health_router, patients_router, records_router
from celery_app import celery_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the application.
    This replaces the deprecated @app.on_event("startup") pattern.
    """
    # Startup: Initialize database
    from repositories import get_database
    logger.info("Initializing database...")
    db = get_database()
    logger.info(f"Database initialized: {db.db_path}")
    
    yield  # Application runs here
    
    # Shutdown: Cleanup resources if needed
    logger.info("Application shutting down...")


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

# Configure CORS to allow telegram_bot to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
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
