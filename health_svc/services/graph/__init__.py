"""
Graph package for health record visualization.

This package contains:
- GraphService: Public orchestration layer for generating health graphs
- PlotlyBuilder: Plotly-specific figure construction

Usage:
    from services.graph import GraphService
    
    service = GraphService()
    html = service.generate_html_graph(records, patient_name)
"""

from services.graph.graph_service import GraphService
from services.graph.plotly_builder import PlotlyBuilder

# Re-export metric registry symbols from core for backward compatibility
# New code should import directly from core.metric_registry
from core.metric_registry import (
    MetricDefinition,
    MetricConfig,
    get_metric,
    get_metric_config,
    list_metrics,
    is_abnormal,
    get_normal_range,
    parse_metric_value,
    parse_timestamp,
    calculate_trend,
    format_metric_value,
    DEFAULT_METRIC_CONFIG,
    RANGE_BAND_COLORS,
    DEFAULT_VISIBLE_METRICS,
)

__all__ = [
    # Primary exports
    'GraphService',
    'PlotlyBuilder',
    # Metric registry exports (from core.metric_registry)
    'MetricDefinition',
    'MetricConfig',
    'get_metric',
    'get_metric_config',
    'list_metrics',
    'is_abnormal',
    'get_normal_range',
    'parse_metric_value',
    'parse_timestamp',
    'calculate_trend',
    'format_metric_value',
    'DEFAULT_METRIC_CONFIG',
    'RANGE_BAND_COLORS',
    'DEFAULT_VISIBLE_METRICS',
]

