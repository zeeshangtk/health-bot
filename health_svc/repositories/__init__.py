"""
Repository layer for database access.

This module contains all database access operations, encapsulating SQL and data persistence logic.
"""
from repositories.patient_repository import PatientRepository
from repositories.health_record_repository import HealthRecordRepository
from repositories.base import get_database, Database

__all__ = [
    "PatientRepository",
    "HealthRecordRepository",
    "get_database",
    "Database",
]

