"""
Domain models for the health service.

This module contains ORM models and internal domain models.
"""
from models.health_record import HealthRecord
from models.patient import Patient

__all__ = ["HealthRecord", "Patient"]

