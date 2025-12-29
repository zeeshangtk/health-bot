"""
FastAPI middleware for observability and operational safety.

This module provides:
- Request/Response logging with request_id propagation
- Request timing for latency tracking
- In-memory metrics collection (Raspberry Pi friendly)

Design Choices:
- Pure ASGI middleware for maximum compatibility
- In-memory metrics with fixed-size buffers (no unbounded growth)
- Minimal overhead for resource-constrained environments
- Request ID in response headers for debugging

Middleware Stack Order (in main.py):
    1. LoggingMiddleware (outermost - captures everything)
    2. CORS Middleware
    3. Application routes
"""

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Optional, Tuple
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging_config import set_request_id, clear_request_id, get_request_id

logger = logging.getLogger(__name__)


# =============================================================================
# IN-MEMORY METRICS COLLECTOR
# =============================================================================
# Lightweight metrics storage suitable for Raspberry Pi.
# Uses fixed-size deques to prevent unbounded memory growth.
# Metrics are exposed via /metrics endpoint for Grafana scraping.

@dataclass
class RequestMetrics:
    """Container for a single request's metrics."""
    timestamp: datetime
    method: str
    path: str
    status_code: int
    duration_ms: float
    request_id: str


@dataclass
class MetricsCollector:
    """
    In-memory metrics collector with fixed-size buffer.
    
    Stores recent requests for latency percentile calculation.
    Thread-safe for concurrent access (deque operations are atomic).
    
    Memory budget (approximate):
    - 1000 requests × ~200 bytes = ~200KB max
    - Safe for Raspberry Pi with limited RAM
    """
    # Fixed-size buffer for latency calculations (last N requests)
    max_history: int = 1000
    
    # Request history for percentile calculations
    _requests: Deque[RequestMetrics] = field(default_factory=lambda: deque(maxlen=1000))
    
    # Counters (simple integers - minimal memory)
    total_requests: int = 0
    total_2xx: int = 0
    total_4xx: int = 0
    total_5xx: int = 0
    
    # Background task counters (updated by Celery task handlers)
    task_success: int = 0
    task_failure: int = 0
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record a completed request's metrics."""
        self._requests.append(metrics)
        self.total_requests += 1
        
        # Categorize by status code
        if 200 <= metrics.status_code < 300:
            self.total_2xx += 1
        elif 400 <= metrics.status_code < 500:
            self.total_4xx += 1
        elif 500 <= metrics.status_code < 600:
            self.total_5xx += 1
    
    def record_task_result(self, success: bool) -> None:
        """Record a background task completion."""
        if success:
            self.task_success += 1
        else:
            self.task_failure += 1
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """
        Calculate latency percentiles from recent requests.
        
        Returns p50, p95, p99 latencies in milliseconds.
        Returns 0 if no data available.
        """
        if not self._requests:
            return {"p50": 0, "p95": 0, "p99": 0}
        
        # Extract durations and sort
        durations = sorted(r.duration_ms for r in self._requests)
        n = len(durations)
        
        def percentile(p: float) -> float:
            """Get the value at percentile p (0-100)."""
            idx = int(n * p / 100)
            return durations[min(idx, n - 1)]
        
        return {
            "p50": round(percentile(50), 2),
            "p95": round(percentile(95), 2),
            "p99": round(percentile(99), 2),
        }
    
    def get_summary(self) -> Dict:
        """
        Get metrics summary for /metrics endpoint.
        
        Returns Prometheus-compatible metric structure.
        """
        latencies = self.get_latency_percentiles()
        
        return {
            "http_requests_total": self.total_requests,
            "http_requests_2xx_total": self.total_2xx,
            "http_requests_4xx_total": self.total_4xx,
            "http_requests_5xx_total": self.total_5xx,
            "http_request_duration_ms_p50": latencies["p50"],
            "http_request_duration_ms_p95": latencies["p95"],
            "http_request_duration_ms_p99": latencies["p99"],
            "background_tasks_success_total": self.task_success,
            "background_tasks_failure_total": self.task_failure,
        }
    
    def get_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        This format can be scraped directly by Prometheus/Grafana Agent.
        """
        summary = self.get_summary()
        lines = [
            "# HELP http_requests_total Total HTTP requests",
            "# TYPE http_requests_total counter",
            f'http_requests_total {summary["http_requests_total"]}',
            "",
            "# HELP http_requests_by_status HTTP requests by status category",
            "# TYPE http_requests_by_status counter",
            f'http_requests_by_status{{status="2xx"}} {summary["http_requests_2xx_total"]}',
            f'http_requests_by_status{{status="4xx"}} {summary["http_requests_4xx_total"]}',
            f'http_requests_by_status{{status="5xx"}} {summary["http_requests_5xx_total"]}',
            "",
            "# HELP http_request_duration_ms Request duration in milliseconds",
            "# TYPE http_request_duration_ms gauge",
            f'http_request_duration_ms{{quantile="0.5"}} {summary["http_request_duration_ms_p50"]}',
            f'http_request_duration_ms{{quantile="0.95"}} {summary["http_request_duration_ms_p95"]}',
            f'http_request_duration_ms{{quantile="0.99"}} {summary["http_request_duration_ms_p99"]}',
            "",
            "# HELP background_tasks_total Background task completions",
            "# TYPE background_tasks_total counter",
            f'background_tasks_total{{result="success"}} {summary["background_tasks_success_total"]}',
            f'background_tasks_total{{result="failure"}} {summary["background_tasks_failure_total"]}',
        ]
        return "\n".join(lines) + "\n"


# Global metrics collector instance
# Singleton pattern - created once, shared across all requests
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics_collector


# =============================================================================
# LOGGING MIDDLEWARE
# =============================================================================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/Response logging middleware with request_id propagation.
    
    Features:
    - Generates unique request_id for each request
    - Logs request start and completion with structured JSON
    - Records latency metrics for Grafana dashboards
    - Adds X-Request-ID header to responses for debugging
    
    Log Output (JSON):
    {
        "timestamp": "...",
        "level": "INFO",
        "message": "Request completed",
        "request_id": "abc-123",
        "extra": {
            "method": "GET",
            "path": "/api/v1/records",
            "status_code": 200,
            "duration_ms": 45.2
        }
    }
    """
    
    # Paths to exclude from detailed logging (reduce noise)
    EXCLUDED_PATHS = {"/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging and metrics collection."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]  # Short UUID for readability
        
        # Set request_id in context for propagation to all logs
        set_request_id(request_id)
        
        # Extract request info
        method = request.method
        path = request.url.path
        
        # Start timing
        start_time = time.perf_counter()
        
        # Log request start (skip noisy endpoints)
        if path not in self.EXCLUDED_PATHS:
            logger.info(
                "Request started",
                extra={
                    "method": method,
                    "path": path,
                    "query": str(request.query_params) if request.query_params else None,
                }
            )
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Log unhandled exception
            logger.exception(
                "Request failed with exception",
                extra={"method": method, "path": path, "error": str(e)}
            )
            raise
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Clear request_id context
            clear_request_id()
        
        # Record metrics
        metrics = RequestMetrics(
            timestamp=datetime.now(timezone.utc),
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        metrics_collector.record_request(metrics)
        
        # Log request completion (skip noisy endpoints)
        if path not in self.EXCLUDED_PATHS:
            log_level = logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                "Request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
        
        # Add request_id to response headers for debugging
        response.headers["X-Request-ID"] = request_id
        
        return response

