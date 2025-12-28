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

# Re-export backward compatibility symbols from metric_registry
from services.graph.metric_registry import (
    MetricConfig,
    get_metric_config,
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
    # Backward compatibility exports
    'MetricConfig',
    'get_metric_config',
    'parse_metric_value',
    'parse_timestamp',
    'calculate_trend',
    'format_metric_value',
    'DEFAULT_METRIC_CONFIG',
    'RANGE_BAND_COLORS',
    'DEFAULT_VISIBLE_METRICS',
]

