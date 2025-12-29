"""
FastAPI Dependency Injection configuration for Health Service API.

This module provides the dependency injection (DI) infrastructure following
the Dependency Inversion Principle. It enables:
- Clean separation between API, Service, and Repository layers
- Easy testing with mock/fake dependencies
- Request-scoped resources with proper cleanup
- Centralized configuration of all dependencies

Architecture Flow:
    API Layer (Routers)
         ↓ Depends()
    Service Layer (Business Logic)
         ↓ Injected
    Repository Layer (Data Access)
         ↓ Injected
    Database (SQLite Connection)

Usage in Routers:
    from core.dependencies import get_health_service, get_patient_service
    
    @router.post("/records")
    async def create_record(
        record: HealthRecordCreate,
        health_service: HealthService = Depends(get_health_service)
    ):
        return health_service.save_record(...)

Testing:
    # Override dependencies in tests
    app.dependency_overrides[get_database] = lambda: test_database
"""
import logging
from functools import lru_cache
from typing import Generator, Optional

from core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE DEPENDENCY
# =============================================================================

# Lazy import to avoid circular dependencies
# The Database class is imported when first needed
_database_instance: Optional["Database"] = None


def get_database() -> "Database":
    """
    Get the database instance (singleton pattern via FastAPI DI).
    
    This function is called once at startup and cached. The database
    is initialized with connection pooling and WAL mode for concurrency.
    
    Returns:
        Database: The configured database instance.
    
    Note:
        Import here to avoid circular imports with repositories.
    """
    global _database_instance
    
    if _database_instance is None:
        from repositories.base import Database
        
        logger.info(f"Initializing database: {settings.database_path}")
        _database_instance = Database(
            db_path=settings.database_path,
            busy_timeout=settings.health_svc_db_busy_timeout
        )
        logger.info("Database initialized successfully")
    
    return _database_instance


def reset_database() -> None:
    """
    Reset the database instance (for testing only).
    
    This allows tests to inject a fresh database instance.
    """
    global _database_instance
    _database_instance = None


# =============================================================================
# REPOSITORY DEPENDENCIES
# =============================================================================

def get_patient_repository() -> "PatientRepository":
    """
    Get a PatientRepository instance with database injected.
    
    This is the repository dependency that handles patient data access.
    The database is injected via get_database().
    
    Returns:
        PatientRepository: Repository for patient CRUD operations.
    """
    from repositories import PatientRepository
    
    db = get_database()
    return PatientRepository(db=db)


def get_health_record_repository() -> "HealthRecordRepository":
    """
    Get a HealthRecordRepository instance with database injected.
    
    Returns:
        HealthRecordRepository: Repository for health record CRUD operations.
    """
    from repositories import HealthRecordRepository
    
    db = get_database()
    return HealthRecordRepository(db=db)


# =============================================================================
# SERVICE DEPENDENCIES
# =============================================================================

def get_patient_service() -> "PatientService":
    """
    Get a PatientService instance with repository injected.
    
    This is the service layer dependency that handles patient business logic.
    The repository is injected via get_patient_repository().
    
    Returns:
        PatientService: Service for patient operations.
    """
    from services import PatientService
    
    patient_repo = get_patient_repository()
    return PatientService(patient_repository=patient_repo)


def get_health_service() -> "HealthService":
    """
    Get a HealthService instance with repositories injected.
    
    This is the service layer dependency that handles health record
    business logic. Both patient and health record repositories are
    injected via their respective dependency functions.
    
    Returns:
        HealthService: Service for health record operations.
    """
    from services import HealthService
    
    patient_repo = get_patient_repository()
    record_repo = get_health_record_repository()
    return HealthService(
        patient_repository=patient_repo,
        health_record_repository=record_repo
    )


def get_graph_service() -> "GraphService":
    """
    Get a GraphService instance.
    
    GraphService is stateless and doesn't require repository injection.
    
    Returns:
        GraphService: Service for generating health record graphs.
    """
    from services.graph import GraphService
    
    return GraphService()


def get_upload_service() -> "UploadService":
    """
    Get an UploadService instance.
    
    UploadService handles file uploads and is configured via settings.
    
    Returns:
        UploadService: Service for file upload operations.
    """
    from services import UploadService
    
    return UploadService(
        upload_dir=settings.health_svc_upload_dir,
        max_size=settings.health_svc_upload_max_size
    )


def get_gemini_service() -> "GeminiService":
    """
    Get a GeminiService instance for AI-based document extraction.
    
    Returns:
        GeminiService: Service for extracting data from medical documents.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not configured.
    """
    from services.gemini_service import GeminiService
    
    return GeminiService(api_key=settings.gemini_api_key)


# =============================================================================
# DEPENDENCY OVERRIDE HELPERS (FOR TESTING)
# =============================================================================

class DependencyOverrides:
    """
    Context manager for temporarily overriding dependencies in tests.
    
    Usage:
        with DependencyOverrides(app) as overrides:
            overrides.set(get_database, mock_database)
            # Run tests with overridden dependency
        # Dependencies restored after context exits
    """
    
    def __init__(self, app):
        self.app = app
        self._original_overrides = {}
    
    def __enter__(self):
        self._original_overrides = self.app.dependency_overrides.copy()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app.dependency_overrides = self._original_overrides
    
    def set(self, dependency, override):
        """Set a dependency override."""
        self.app.dependency_overrides[dependency] = override
    
    def clear(self):
        """Clear all overrides."""
        self.app.dependency_overrides = self._original_overrides.copy()


