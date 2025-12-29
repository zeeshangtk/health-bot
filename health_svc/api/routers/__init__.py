"""
API routers module.

This module contains all API route definitions organized by domain.
"""
from api.routers.health import router as health_router
from api.routers.patients import router as patients_router
from api.routers.records import router as records_router
from api.routers.meta import router as meta_router

__all__ = ["health_router", "patients_router", "records_router", "meta_router"]

