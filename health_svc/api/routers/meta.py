"""
Meta router - metric definitions and configuration endpoints.

This router provides access to metric definitions from metrics.yaml,
enabling the Telegram bot to dynamically consume metric metadata
without hardcoding values.

This eliminates duplication between backend and Telegram bot:
- Single source of truth: metrics.yaml
- API endpoint exposes metric definitions
- Telegram bot fetches and caches definitions

No authentication required for read-only metadata access.
"""
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.metric_registry import (
    list_metrics,
    get_metric,
    get_metric_config,
    RANGE_BAND_COLORS,
    DEFAULT_VISIBLE_METRICS,
    MetricDefinition,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/meta",
    tags=["Metadata"],
    # No authentication - these are public read-only endpoints
)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class MetricDefinitionResponse(BaseModel):
    """Single metric definition for API response."""
    canonical_name: str
    display_name: str
    color: str
    range: Optional[List[float]] = None  # [low, high] or null
    unit: str
    axis: str  # y1 or y2
    category: str
    description: str
    aliases: List[str]


class MetricsListResponse(BaseModel):
    """Response containing all metric definitions."""
    metrics: List[MetricDefinitionResponse]
    default_visible: List[str]
    categories: Dict[str, str]  # category -> band color


def _metric_to_response(metric: MetricDefinition) -> MetricDefinitionResponse:
    """Convert internal MetricDefinition to API response model."""
    return MetricDefinitionResponse(
        canonical_name=metric.canonical_name,
        display_name=metric.display_name,
        color=metric.color,
        range=list(metric.range) if metric.range else None,
        unit=metric.unit,
        axis=metric.axis,
        category=metric.category,
        description=metric.description,
        aliases=list(metric.aliases),
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "/metrics",
    response_model=MetricsListResponse,
    summary="List all metric definitions",
    description="Get all health metric definitions from the central registry (metrics.yaml). "
                "Includes canonical names, units, normal ranges, colors, and aliases. "
                "Use this to dynamically populate UI choices in Telegram bot."
)
async def list_metric_definitions() -> MetricsListResponse:
    """
    Get all metric definitions.
    
    Returns:
    - metrics: List of all metric definitions with full metadata
    - default_visible: List of metric canonical names shown by default
    - categories: Map of category names to their visualization colors
    
    Use this endpoint to:
    - Populate record type choices in Telegram bot
    - Get display units for measurements
    - Determine normal ranges for value validation
    - Apply consistent colors in visualizations
    
    This data comes from metrics.yaml - the single source of truth.
    """
    all_metrics = list_metrics()
    
    return MetricsListResponse(
        metrics=[_metric_to_response(m) for m in all_metrics.values()],
        default_visible=list(DEFAULT_VISIBLE_METRICS),
        categories=RANGE_BAND_COLORS,
    )


@router.get(
    "/metrics/{metric_name}",
    response_model=MetricDefinitionResponse,
    summary="Get single metric definition",
    description="Get detailed definition for a specific metric by canonical name or alias."
)
async def get_metric_definition(
    metric_name: str,
    fallback_to_default: bool = Query(
        True,
        description="If True, return default metric config for unknown names. "
                    "If False, return 404 for unknown metrics."
    )
) -> MetricDefinitionResponse:
    """
    Get a single metric's definition.
    
    Path Parameters:
    - **metric_name**: Canonical metric name or alias (case-insensitive)
    
    Query Parameters:
    - **fallback_to_default**: Whether to return default config for unknown metrics
    
    Examples:
    - GET /api/v1/meta/metrics/creatinine
    - GET /api/v1/meta/metrics/rbs (alias for "random blood sugar")
    - GET /api/v1/meta/metrics/hb (alias for "haemoglobin")
    
    Returns metric definition with all metadata.
    """
    if fallback_to_default:
        metric = get_metric_config(metric_name)
    else:
        metric = get_metric(metric_name)
    
    return _metric_to_response(metric)


@router.get(
    "/metrics/category/{category}",
    response_model=List[MetricDefinitionResponse],
    summary="Get metrics by category",
    description="Get all metrics belonging to a specific category (e.g., kidney, sugar, blood)."
)
async def list_metrics_by_category(category: str) -> List[MetricDefinitionResponse]:
    """
    Get all metrics in a category.
    
    Path Parameters:
    - **category**: Category name (kidney, sugar, electrolyte, blood, liver, lipid, other)
    
    Returns list of metrics in the specified category.
    """
    all_metrics = list_metrics()
    
    # Filter by category (case-insensitive)
    category_lower = category.lower()
    filtered = [
        m for m in all_metrics.values()
        if m.category.lower() == category_lower
    ]
    
    return [_metric_to_response(m) for m in filtered]


@router.get(
    "/record-types",
    summary="Get available record types for Telegram bot",
    description="Simplified endpoint returning just the record type names and units "
                "for use in Telegram bot inline keyboard choices."
)
async def get_record_types() -> Dict[str, Any]:
    """
    Get simplified record type list for Telegram bot.
    
    Returns a simple structure optimized for building Telegram inline keyboards:
    - types: List of {name, display_name, unit, category}
    
    This endpoint is designed for:
    - Building /add_record keyboard choices
    - Showing unit hints during value entry
    - Grouping metrics by category for better UX
    """
    all_metrics = list_metrics()
    
    # Group by category for better Telegram keyboard layout
    by_category: Dict[str, List[Dict[str, str]]] = {}
    
    for metric in all_metrics.values():
        category = metric.category
        if category not in by_category:
            by_category[category] = []
        
        by_category[category].append({
            "name": metric.canonical_name,
            "display_name": metric.display_name,
            "unit": metric.unit,
        })
    
    return {
        "types": by_category,
        "categories": list(by_category.keys()),
    }


