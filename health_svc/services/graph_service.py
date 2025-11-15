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
                title=dict(
                    text=f"No health records found for {patient_name}",
                    font=dict(size=16)
                ),
                xaxis_title="Timestamp",
                yaxis_title="Value",
                height=400,
                autosize=True,
                margin=dict(l=50, r=30, t=60, b=50)
            )
            return pio.to_html(
                fig, 
                include_plotlyjs='cdn',
                config=self._get_mobile_config()
            )
        
        # Group records by record_type
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            records_by_type[record.record_type].append(record)
        
        # Determine default visibility: Creatinine if present, otherwise first record type
        record_types = list(records_by_type.keys())
        default_visible_type = None
        
        # Check for Creatinine (case-insensitive)
        for rt in record_types:
            if rt.lower() in ['creatinine', 'creatine']:
                default_visible_type = rt
                break
        
        # If no Creatinine found, use first record type
        if default_visible_type is None and record_types:
            default_visible_type = record_types[0]
        
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
            
            # Determine if this trace should be visible by default
            # Use "legendonly" for non-default traces so they appear in legend but are hidden on graph
            # Users can click them to toggle visibility
            if default_visible_type:
                is_visible = True if (record_type == default_visible_type) else "legendonly"
            else:
                is_visible = True
            
            # Add trace to figure with explicit line configuration
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                mode='lines+markers',
                name=trace_name,
                visible=is_visible,
                showlegend=True,  # Explicitly show in legend
                line=dict(
                    width=2.5,
                    shape='linear'  # Connect points with straight lines
                ),
                marker=dict(
                    size=10,
                    line=dict(width=1.5, color='white')
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
        
        # Update layout with mobile-friendly configuration
        fig.update_layout(
            title=dict(
                text=f"Health Records for {patient_name}",
                font=dict(size=18),
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title=dict(text="Timestamp", font=dict(size=14)),
                type="date",  # Ensure x-axis is treated as datetime
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickfont=dict(size=12)
            ),
            yaxis=dict(
                title=dict(text="Value", font=dict(size=14)),
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickfont=dict(size=12)
            ),
            hovermode='x unified',
            showlegend=True,  # Explicitly show legend
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,  # Position just below the x-axis label (Timestamp)
                xanchor="center",
                x=0.5,
                font=dict(size=12),
                itemclick="toggle",  # Toggle individual traces independently
                itemdoubleclick="toggle",
                bgcolor="rgba(255,255,255,0.9)",  # Semi-transparent white background
                bordercolor="rgba(0,0,0,0.3)",
                borderwidth=1
            ),
            height=500,
            autosize=True,
            margin=dict(l=60, r=30, t=80, b=120),  # Bottom margin for legend below x-axis
            template="plotly_white",
            # Mobile-friendly responsive settings
            dragmode='pan',  # Better for touch devices
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="black",
                font_size=12
            )
        )
        
        # Generate HTML with mobile-optimized config
        html_content = pio.to_html(
            fig, 
            include_plotlyjs='cdn',
            config=self._get_mobile_config(),
            div_id="health-graph"
        )
        
        # Add mobile-responsive CSS wrapper
        mobile_css = """
        <style>
            #health-graph {
                width: 100% !important;
                max-width: 100%;
                overflow-x: auto;
            }
            .js-plotly-plot {
                width: 100% !important;
                max-width: 100%;
            }
            @media (max-width: 768px) {
                #health-graph {
                    font-size: 14px;
                }
                .plotly .modebar {
                    display: none !important;
                }
            }
            @media (max-width: 480px) {
                #health-graph {
                    font-size: 12px;
                }
            }
        </style>
        """
        
        # Insert CSS before the plotly div
        html_content = html_content.replace('<body>', f'<body>{mobile_css}')
        
        return html_content
    
    def _get_mobile_config(self) -> Dict[str, Any]:
        """
        Get Plotly configuration optimized for mobile devices.
        
        Returns:
            Dict with mobile-friendly Plotly config settings
        """
        return {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'responsive': True,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'health_records',
                'height': 600,
                'width': 1200,
                'scale': 1
            },
            'scrollZoom': True,  # Enable pinch-to-zoom on mobile
            'doubleClick': 'reset',
            'showTips': True
        }
    
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

