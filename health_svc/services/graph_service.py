"""
Service layer for generating health record visualization graphs.
"""
import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

import plotly.graph_objects as go
import plotly.io as pio

from api.schemas import HealthRecordResponse

logger = logging.getLogger(__name__)


class GraphService:
    """Service layer for generating health record visualization graphs."""
    
    def generate_html_graph(self, records: List[HealthRecordResponse], patient_name: str) -> str:
        """
        Generate an HTML graph visualization of health records using Plotly.
        
        Args:
            records: List of health record responses
            patient_name: Name of the patient (for graph title)
        
        Returns:
            str: HTML content containing the interactive Plotly graph
        """
        if not records:
            # Return empty graph HTML if no records
            fig = go.Figure()
            fig.update_layout(
                title=f"No health records found for {patient_name}",
                xaxis_title="Timestamp",
                yaxis_title="Value"
            )
            return pio.to_html(fig, include_plotlyjs='cdn')
        
        # Group records by record_type
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            records_by_type[record.record_type].append(record)
        
        # Create figure
        fig = go.Figure()
        
        # Add a trace for each record type
        for record_type, type_records in records_by_type.items():
            # Parse timestamps and sort by datetime to ensure chronological order
            # This ensures records of the same type are connected across different dates
            records_with_dt = [
                (datetime.fromisoformat(r.timestamp), r) 
                for r in type_records
            ]
            sorted_records_with_dt = sorted(records_with_dt, key=lambda x: x[0])
            
            # Extract timestamps and values in chronological order
            timestamps = [dt for dt, _ in sorted_records_with_dt]
            values = []
            units = []
            
            for _, record in sorted_records_with_dt:
                # Try to convert value to float, handle special cases
                value = self._parse_value(record.value)
                values.append(value)
                units.append(record.unit or "")
            
            # Get unique unit for this record type (for y-axis label)
            unique_units = list(set([u for u in units if u]))
            unit_label = f" ({unique_units[0]})" if unique_units else ""
            
            # Create trace name with unit if available
            trace_name = f"{record_type}{unit_label}" if unique_units else record_type
            
            # Add trace to figure with explicit line configuration
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                mode='lines+markers',
                name=trace_name,
                line=dict(
                    width=2,
                    shape='linear'  # Connect points with straight lines
                ),
                marker=dict(
                    size=8,
                    line=dict(width=1)
                ),
                connectgaps=True, 
                hovertemplate=(
                    f"<b>{record_type}</b><br>" +
                    "Timestamp: %{x}<br>" +
                    "Value: %{y}" +
                    (f" {unique_units[0]}" if unique_units else "") +
                    "<extra></extra>"
                )
            ))
        
        # Update layout with proper datetime axis configuration
        fig.update_layout(
            title=f"Health Records for {patient_name}",
            xaxis=dict(
                title="Timestamp",
                type="date",  # Ensure x-axis is treated as datetime
                showgrid=True,
                gridwidth=1
            ),
            yaxis_title="Value",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=600,
            template="plotly_white"
        )
        
        # Generate HTML
        html_content = pio.to_html(fig, include_plotlyjs='cdn')
        return html_content
    
    def _parse_value(self, value_str: str) -> float:
        """
        Parse a value string to float.
        
        Handles various formats:
        - Simple numbers: "120" -> 120.0
        - Decimals: "120.5" -> 120.5
        - Blood pressure: "120/80" -> 120.0 (systolic)
        - Other formats: attempts to extract first number
        
        Args:
            value_str: String representation of the value
        
        Returns:
            float: Parsed numeric value
        """
        try:
            # Try direct conversion first
            return float(value_str)
        except ValueError:
            # Handle blood pressure format (e.g., "120/80")
            if '/' in value_str:
                parts = value_str.split('/')
                if parts:
                    try:
                        return float(parts[0].strip())
                    except ValueError:
                        pass
            
            # Try to extract first number from string
            match = re.search(r'(\d+\.?\d*)', value_str)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
            
            # If all else fails, return 0.0
            logger.warning(f"Could not parse value '{value_str}', using 0.0")
            return 0.0

