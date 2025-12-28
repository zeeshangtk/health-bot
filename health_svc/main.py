"""
FastAPI application entry point for Health Service API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import API_HOST, API_PORT, API_RELOAD
from api.routers import health_router, patients_router, records_router
from celery_app import celery_app

# Create FastAPI app
app = FastAPI(
    title="Health Service API",
    description="REST API for health record management. Track and manage patient health records including blood pressure, weight, temperature, and other measurements.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    from repositories import get_database
    # This will initialize the database schema
    get_database()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
