"""
Health, readiness, and metrics endpoints for operational visibility.

This module provides:
- /health: Liveness probe (is the app running?)
- /ready: Readiness probe (are dependencies available?)
- /metrics: Prometheus-compatible metrics for Grafana scraping

These endpoints are designed for:
- Kubernetes/Docker health checks
- Grafana dashboard integration
- Low-overhead operation on Raspberry Pi

Design Choices:
- No authentication required (internal/infrastructure use)
- Lightweight dependency checks (non-blocking)
- Machine-readable JSON responses
- Prometheus text format for metrics
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi import APIRouter, Response
from pydantic import BaseModel

from core.config import settings, REDIS_URL
from core.middleware import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Observability"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    """Response model for /health endpoint."""
    status: str  # "healthy" or "unhealthy"
    version: str
    timestamp: str  # ISO 8601 UTC


class DependencyStatus(BaseModel):
    """Status of a single dependency."""
    name: str
    status: str  # "ok", "degraded", "unavailable"
    latency_ms: float | None = None
    message: str | None = None


class ReadyResponse(BaseModel):
    """Response model for /ready endpoint."""
    status: str  # "ready", "degraded", "not_ready"
    dependencies: List[DependencyStatus]
    timestamp: str


class MetricsResponse(BaseModel):
    """Response model for JSON metrics endpoint."""
    http_requests_total: int
    http_requests_2xx_total: int
    http_requests_4xx_total: int
    http_requests_5xx_total: int
    http_request_duration_ms_p50: float
    http_request_duration_ms_p95: float
    http_request_duration_ms_p99: float
    background_tasks_success_total: int
    background_tasks_failure_total: int


# =============================================================================
# HEALTH ENDPOINT (LIVENESS)
# =============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Check if the application is running. Returns immediately without checking dependencies. "
                "Use this for Kubernetes liveness probes or basic uptime monitoring."
)
async def health_check() -> HealthResponse:
    """
    Liveness probe - is the application process alive?
    
    This endpoint:
    - Returns immediately (no I/O)
    - Always returns 200 if the app is running
    - Does NOT check dependencies (that's what /ready is for)
    
    Use for:
    - Container orchestration liveness probes
    - Basic "is it up?" checks
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


# =============================================================================
# READINESS ENDPOINT
# =============================================================================

async def _check_database() -> DependencyStatus:
    """
    Check SQLite database connectivity.
    
    Performs a lightweight query to verify the database is accessible.
    Non-blocking and fast for Raspberry Pi.
    """
    import time
    from core.dependencies import get_database
    
    start = time.perf_counter()
    try:
        db = get_database()
        # Simple connectivity check - execute a trivial query
        with db.get_connection() as conn:
            conn.execute("SELECT 1")
        
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyStatus(
            name="database",
            status="ok",
            latency_ms=round(latency_ms, 2),
            message="SQLite connection healthy"
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.error("Database health check failed", extra={"error": str(e)})
        return DependencyStatus(
            name="database",
            status="unavailable",
            latency_ms=round(latency_ms, 2),
            message=f"Connection failed: {type(e).__name__}"
        )


async def _check_celery() -> DependencyStatus:
    """
    Check Celery/Redis connectivity for background tasks.
    
    Attempts to ping Redis to verify the message broker is available.
    Returns "degraded" if Redis is down but app can still serve requests.
    """
    import time
    
    start = time.perf_counter()
    try:
        # Try to ping Redis via celery's connection
        import redis
        
        # Parse Redis URL and create client
        client = redis.from_url(REDIS_URL, socket_timeout=2)
        client.ping()
        
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyStatus(
            name="celery_broker",
            status="ok",
            latency_ms=round(latency_ms, 2),
            message="Redis broker healthy"
        )
    except ImportError:
        # Redis library not installed - Celery not being used
        return DependencyStatus(
            name="celery_broker",
            status="ok",
            latency_ms=0,
            message="Redis client not installed (Celery disabled)"
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning("Celery broker health check failed", extra={"error": str(e)})
        return DependencyStatus(
            name="celery_broker",
            status="degraded",
            latency_ms=round(latency_ms, 2),
            message=f"Broker unavailable: {type(e).__name__}"
        )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
    description="Check if the application is ready to serve requests. "
                "Verifies critical dependencies (database, message broker) are available. "
                "Returns 503 if not ready."
)
async def readiness_check(response: Response) -> ReadyResponse:
    """
    Readiness probe - can the application handle requests?
    
    Checks:
    1. Database connectivity (SQLite)
    2. Background task broker (Redis/Celery) if configured
    
    Returns:
    - 200 with status="ready" if all dependencies are healthy
    - 200 with status="degraded" if non-critical dependencies are down
    - 503 with status="not_ready" if critical dependencies are down
    
    Use for:
    - Kubernetes readiness probes
    - Load balancer health checks
    - Grafana dashboard dependency monitoring
    """
    # Check all dependencies concurrently
    db_status = await _check_database()
    celery_status = await _check_celery()
    
    dependencies = [db_status, celery_status]
    
    # Determine overall status
    # Database is critical - if it's down, we're not ready
    # Celery is non-critical - if it's down, we're degraded but can serve requests
    critical_down = any(
        d.status == "unavailable" 
        for d in dependencies 
        if d.name == "database"
    )
    
    any_degraded = any(d.status in ("degraded", "unavailable") for d in dependencies)
    
    if critical_down:
        status = "not_ready"
        response.status_code = 503
    elif any_degraded:
        status = "degraded"
    else:
        status = "ready"
    
    return ReadyResponse(
        status=status,
        dependencies=dependencies,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


# =============================================================================
# METRICS ENDPOINT
# =============================================================================

@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Export metrics in Prometheus text format for Grafana scraping. "
                "Includes HTTP request counts, latency percentiles, and background task stats."
)
async def get_metrics() -> Response:
    """
    Export metrics in Prometheus text format.
    
    Metrics exposed:
    - http_requests_total: Total request count
    - http_requests_by_status{status="2xx|4xx|5xx"}: Requests by status category
    - http_request_duration_ms{quantile="0.5|0.95|0.99"}: Latency percentiles
    - background_tasks_total{result="success|failure"}: Task completion counts
    
    Scrape configuration (prometheus.yml):
        scrape_configs:
          - job_name: 'health-svc'
            static_configs:
              - targets: ['localhost:8000']
            metrics_path: /metrics
    """
    collector = get_metrics_collector()
    prometheus_text = collector.get_prometheus_format()
    
    return Response(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get(
    "/metrics/json",
    response_model=MetricsResponse,
    summary="JSON metrics",
    description="Export metrics in JSON format for custom dashboards or API consumers."
)
async def get_metrics_json() -> MetricsResponse:
    """
    Export metrics in JSON format.
    
    Useful for:
    - Custom dashboard integrations
    - Telegram bot status commands
    - Debugging and development
    """
    collector = get_metrics_collector()
    summary = collector.get_summary()
    
    return MetricsResponse(**summary)


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@router.get(
    "/",
    summary="API root",
    description="Root endpoint with basic API information."
)
async def root() -> Dict[str, Any]:
    """
    Root endpoint - basic API information.
    
    Returns service name, version, and links to documentation.
    """
    return {
        "service": "Health Service API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "metrics": "/metrics"
    }
