"""
Service layer for generating health record visualization graphs.

Features:
- Dual Y-axis support for metrics with different scales
- Blood pressure high-low chart visualization
- Semantic color coding by category
- Abnormal value highlighting (filled markers + symbols)
- Touch-friendly markers and horizontal legend
- Educational metric descriptions in tooltips
- Summary panel with latest readings
- Date range filters and slider
- Spline curves for smooth visualization

This module orchestrates data preparation and Plotly figure construction.
Data preparation is delegated to DataPreparationService.
Figure construction is delegated to PlotlyBuilder.
Metric configuration and parsing is handled by metric_registry.
"""

import logging
from typing import List, Optional

import plotly.io as pio

from api.schemas import HealthRecordResponse
from services.data_preparation_service import DataPreparationService
from services.graph.plotly_builder import PlotlyBuilder

logger = logging.getLogger(__name__)


# =============================================================================
# GRAPH SERVICE
# =============================================================================

class GraphService:
    """
    Service for generating enhanced health record graphs with dual Y-axis support.
    
    This is the public orchestration layer that combines:
    - Data preparation via DataPreparationService
    - Figure construction via PlotlyBuilder
    
    All data parsing and normalization is delegated to DataPreparationService.
    All Plotly-specific figure construction is delegated to PlotlyBuilder.
    This class focuses on orchestrating the flow between these components.
    """

    def __init__(
        self,
        data_preparation_service: Optional[DataPreparationService] = None,
        plotly_builder: Optional[PlotlyBuilder] = None,
    ):
        """
        Initialize GraphService.
        
        Args:
            data_preparation_service: Optional service for data preparation.
                                     If not provided, a default instance is created.
            plotly_builder: Optional builder for Plotly figure construction.
                           If not provided, a default instance is created.
        """
        self._data_prep = data_preparation_service or DataPreparationService()
        self._builder = plotly_builder or PlotlyBuilder()

    def generate_html_graph(self, records: List[HealthRecordResponse], patient_name: str) -> str:
        """Generate complete HTML with interactive Plotly graph."""
        if not records:
            return self._generate_empty_graph(patient_name)

        # Delegate all data preparation to the dedicated service
        dataset = self._data_prep.prepare_dataset(records)
        
        # Build the figure using PlotlyBuilder
        fig = self._builder.create_figure()

        # Handle Blood Pressure specially (systolic/diastolic as range chart)
        if dataset.blood_pressure and not dataset.blood_pressure.is_empty():
            self._builder.add_blood_pressure_trace(fig, dataset.blood_pressure)

        # Add standard traces
        for metric_name, metric_data in dataset.metrics.items():
            is_visible = metric_name in dataset.visible_metrics
            trace = self._builder.create_metric_trace(metric_data, is_visible)
            fig.add_trace(trace)

        # Apply layout and add summary
        self._builder.apply_layout(fig, patient_name)
        self._builder.add_summary_panel(fig, dataset.summaries, dataset.date_range[1])

        html_content = pio.to_html(
            fig,
            include_plotlyjs='cdn',
            config=self._builder.get_mobile_config(),
            div_id="health-graph"
        )

        return self._builder.inject_mobile_css(html_content)

    def _generate_empty_graph(self, patient_name: str) -> str:
        """Generate styled placeholder graph when no records exist."""
        fig = self._builder.create_figure()
        self._builder.apply_empty_layout(fig, patient_name)
        
        html = pio.to_html(
            fig,
            include_plotlyjs='cdn',
            config=self._builder.get_mobile_config()
        )
        return self._builder.inject_mobile_css(html)

