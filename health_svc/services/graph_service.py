"""
Service layer for generating health record visualization graphs.

This module provides a mobile-optimized, clinically-informed Plotly graph 
generator for health records. Features include:
- Semantic color coding by metric category (kidney, sugar, electrolytes)
- Reference range bands for key metrics (informational only)
- Touch-friendly markers and legends optimized for Telegram/mobile viewing
- Color-blind friendly palette
- Formatted hover tooltips with proper units
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

import plotly.graph_objects as go
import plotly.io as pio

from api.schemas import HealthRecordResponse

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION: Semantic Colors, Reference Ranges, and Defaults
# =============================================================================

# Color-blind friendly palette organized by clinical category
# Using distinct hues that remain distinguishable with color vision deficiencies
METRIC_COLORS: Dict[str, str] = {
    # Kidney Function - Blues (easily distinguishable shades)
    'creatinine': '#1E88E5',           # Bright blue
    'serum creatinine': '#1E88E5',
    'blood urea': '#1565C0',           # Deep blue
    'serum urea': '#1565C0',
    'blood urea nitrogen': '#0D47A1',  # Navy blue
    'bun': '#0D47A1',
    'egfr': '#42A5F5',                 # Light blue
    
    # Blood Sugar - Greens (distinct from blues)
    'random blood sugar': '#43A047',    # Medium green
    'fasting blood sugar': '#2E7D32',   # Dark green
    'blood sugar': '#66BB6A',           # Light green
    'hba1c': '#1B5E20',                 # Deep green
    'glucose': '#4CAF50',               # Standard green
    
    # Electrolytes - Purples/Magentas
    'sodium': '#8E24AA',               # Purple
    'potassium': '#AB47BC',            # Light purple
    'chloride': '#7B1FA2',             # Deep purple
    'calcium': '#BA68C8',              # Lavender
    'phosphorus': '#6A1B9A',           # Dark purple
    'magnesium': '#CE93D8',            # Pale purple
    
    # Blood/Hematology - Reds/Warm tones
    'haemoglobin': '#E53935',          # Red
    'hemoglobin': '#E53935',
    'hematocrit': '#C62828',           # Dark red
    'rbc': '#EF5350',                  # Light red
    'wbc': '#F44336',                  # Medium red
    'platelets': '#D32F2F',            # Deep red
    
    # Liver Function - Oranges/Ambers
    'bilirubin': '#FB8C00',            # Orange
    'sgpt': '#F57C00',                 # Deep orange
    'alt': '#F57C00',
    'sgot': '#EF6C00',                 # Darker orange
    'ast': '#EF6C00',
    'alkaline phosphatase': '#FF9800', # Amber
    
    # Lipids - Teals
    'cholesterol': '#00897B',          # Teal
    'triglycerides': '#00796B',        # Dark teal
    'hdl': '#26A69A',                  # Light teal
    'ldl': '#004D40',                  # Deep teal
    
    # Other - Neutrals/Grays
    'uric acid': '#757575',            # Gray
    'protein': '#616161',              # Dark gray
    'albumin': '#9E9E9E',              # Medium gray
}

# General adult reference ranges (informational only - not for diagnosis)
# Format: (min_normal, max_normal, unit)
NORMAL_RANGES: Dict[str, Tuple[float, float, str]] = {
    # Kidney Function
    'creatinine': (0.6, 1.2, 'mg/dl'),
    'serum creatinine': (0.6, 1.2, 'mg/dl'),
    'blood urea': (15.0, 45.0, 'mg/dl'),
    'serum urea': (15.0, 45.0, 'mg/dl'),
    'blood urea nitrogen': (7.0, 20.0, 'mg/dl'),
    'bun': (7.0, 20.0, 'mg/dl'),
    
    # Blood Sugar
    'random blood sugar': (70.0, 140.0, 'mg/dl'),
    'fasting blood sugar': (70.0, 100.0, 'mg/dl'),
    'blood sugar': (70.0, 140.0, 'mg/dl'),
    'hba1c': (4.0, 5.6, '%'),
    
    # Electrolytes
    'sodium': (136.0, 145.0, 'mMol/L'),
    'potassium': (3.5, 5.0, 'mMol/L'),
    'chloride': (98.0, 106.0, 'mMol/L'),
    'calcium': (8.5, 10.5, 'mg/dl'),
    
    # Blood
    'haemoglobin': (12.0, 17.5, 'g/dl'),
    'hemoglobin': (12.0, 17.5, 'g/dl'),
    
    # Other
    'uric acid': (2.4, 7.0, 'mg/dl'),
}

# Fallback units when not provided in data
DEFAULT_UNITS: Dict[str, str] = {
    'creatinine': 'mg/dl',
    'serum creatinine': 'mg/dl',
    'blood urea': 'mg/dl',
    'serum urea': 'mg/dl',
    'blood urea nitrogen': 'mg/dl',
    'bun': 'mg/dl',
    'random blood sugar': 'mg/dl',
    'fasting blood sugar': 'mg/dl',
    'blood sugar': 'mg/dl',
    'hba1c': '%',
    'sodium': 'mMol/L',
    'potassium': 'mMol/L',
    'chloride': 'mMol/L',
    'calcium': 'mg/dl',
    'haemoglobin': 'g/dl',
    'hemoglobin': 'g/dl',
    'uric acid': 'mg/dl',
}

# Metrics to show by default (ordered by clinical priority)
# These are commonly monitored and clinically relevant at a glance
DEFAULT_VISIBLE_METRICS: List[str] = [
    'creatinine',
    'serum creatinine',
    'blood urea',
    'random blood sugar',
    'haemoglobin',
    'hemoglobin',
]

# Reference band colors by category (low opacity for subtle background)
RANGE_BAND_COLORS: Dict[str, str] = {
    'kidney': 'rgba(30, 136, 229, 0.12)',      # Blue tint
    'sugar': 'rgba(67, 160, 71, 0.12)',        # Green tint
    'electrolyte': 'rgba(142, 36, 170, 0.12)', # Purple tint
    'blood': 'rgba(229, 57, 53, 0.12)',        # Red tint
    'other': 'rgba(117, 117, 117, 0.12)',      # Gray tint
}


class GraphService:
    """
    Service layer for generating health record visualization graphs.
    
    Produces mobile-optimized, clinically-informed Plotly graphs with:
    - Semantic color coding by metric category
    - Optional reference range bands
    - Touch-friendly sizing for Telegram/mobile
    - Formatted hover tooltips
    """
    
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
            return self._generate_empty_graph(patient_name)
        
        # Group records by record_type
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            records_by_type[record.record_type].append(record)
        
        # Determine which metrics should be visible by default
        visible_metrics = self._get_default_visible_metrics(list(records_by_type.keys()))
        
        # Create figure
        fig = go.Figure()
        
        # Track which reference bands we've added (avoid duplicates)
        added_reference_bands: set = set()
        
        # Collect all values to determine Y-axis range for reference bands
        all_values: List[float] = []
        date_range: Tuple[datetime, datetime] = self._get_date_range(records)
        
        # First pass: collect all values and add traces
        for record_type, type_records in records_by_type.items():
            trace_data = self._prepare_trace_data(record_type, type_records)
            all_values.extend(trace_data['values'])
            
            # Determine visibility
            is_visible = self._should_be_visible(record_type, visible_metrics)
            
            # Add trace with semantic styling
            fig.add_trace(self._create_trace(
                record_type=record_type,
                trace_data=trace_data,
                is_visible=is_visible
            ))
        
        # Second pass: add reference range bands for visible metrics
        for metric in visible_metrics:
            if metric in records_by_type and metric not in added_reference_bands:
                self._add_reference_band(fig, metric, date_range, all_values)
                added_reference_bands.add(metric)
        
        # Update layout with mobile-friendly configuration
        self._apply_layout(fig, patient_name, date_range)
        
        # Generate HTML with mobile-optimized config
        html_content = pio.to_html(
            fig, 
            include_plotlyjs='cdn',
            config=self._get_mobile_config(),
            div_id="health-graph"
        )
        
        # Add mobile-responsive CSS
        html_content = self._inject_mobile_css(html_content)
        
        return html_content
    
    def _generate_empty_graph(self, patient_name: str) -> str:
        """Generate placeholder graph when no records exist."""
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text=f"<b>Health Records</b><br><sup>{patient_name}</sup>",
                font=dict(size=20, color='#212121'),
                x=0.5,
                xanchor='center',
            ),
            xaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
            ),
            yaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
            ),
            height=450,
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50),
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            annotations=[
                {
                    'text': '📊',
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.5,
                    'y': 0.6,
                    'showarrow': False,
                    'font': {'size': 48}
                },
                {
                    'text': '<b>No health records yet</b>',
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.5,
                    'y': 0.42,
                    'showarrow': False,
                    'font': {'size': 18, 'color': '#424242'}
                },
                {
                    'text': 'Upload a lab report to see your health trends',
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.5,
                    'y': 0.32,
                    'showarrow': False,
                    'font': {'size': 14, 'color': '#757575'}
                }
            ]
        )
        
        html_content = pio.to_html(
            fig, 
            include_plotlyjs='cdn',
            config=self._get_mobile_config()
        )
        return self._inject_mobile_css(html_content)
    
    def _get_default_visible_metrics(self, available_metrics: List[str]) -> List[str]:
        """
        Determine which metrics should be visible by default.
        
        Prioritizes clinically important metrics that exist in the data.
        Shows up to 3 metrics to avoid cluttering the initial view.
        """
        visible = []
        normalized_available = {m.lower(): m for m in available_metrics}
        
        # First, check for priority metrics
        for priority_metric in DEFAULT_VISIBLE_METRICS:
            if priority_metric in normalized_available:
                visible.append(normalized_available[priority_metric])
                if len(visible) >= 3:
                    break
        
        # If we have fewer than 2 visible, add more from available
        if len(visible) < 2:
            for metric in available_metrics:
                if metric not in visible:
                    visible.append(metric)
                    if len(visible) >= 2:
                        break
        
        return visible
    
    def _should_be_visible(self, record_type: str, visible_metrics: List[str]) -> bool:
        """Check if a record type should be visible by default."""
        return record_type in visible_metrics
    
    def _get_date_range(self, records: List[HealthRecordResponse]) -> Tuple[datetime, datetime]:
        """Get the min and max dates from records."""
        dates = []
        for record in records:
            try:
                dt = datetime.fromisoformat(record.timestamp)
                dates.append(dt)
            except (ValueError, AttributeError):
                continue
        
        if not dates:
            now = datetime.now()
            return (now, now)
        
        return (min(dates), max(dates))
    
    def _prepare_trace_data(
        self, 
        record_type: str, 
        type_records: List[HealthRecordResponse]
    ) -> Dict[str, Any]:
        """
        Prepare data for a single trace.
        
        Returns dict with timestamps, values, units, formatted dates,
        percent changes, and abnormal status for each value.
        """
        # Parse and sort by datetime
        records_with_dt = []
        for r in type_records:
            try:
                dt = datetime.fromisoformat(r.timestamp)
                records_with_dt.append((dt, r))
            except (ValueError, AttributeError):
                continue
        
        sorted_records = sorted(records_with_dt, key=lambda x: x[0])
        
        timestamps = []
        values = []
        units = []
        formatted_dates = []
        
        for dt, record in sorted_records:
            timestamps.append(dt)
            values.append(self._parse_value(record.value))
            units.append(record.unit or self._get_default_unit(record_type))
            formatted_dates.append(dt.strftime('%b %d, %Y'))
        
        # Get consistent unit for this metric
        unique_units = list(set([u for u in units if u]))
        unit = unique_units[0] if unique_units else self._get_default_unit(record_type)
        
        # Calculate percent change from previous value
        percent_changes = self._calculate_percent_changes(values)
        
        # Determine which values are abnormal (outside normal range)
        is_abnormal = self._check_abnormal_values(record_type, values)
        
        return {
            'timestamps': timestamps,
            'values': values,
            'unit': unit,
            'formatted_dates': formatted_dates,
            'percent_changes': percent_changes,
            'is_abnormal': is_abnormal,
        }
    
    def _calculate_percent_changes(self, values: List[float]) -> List[str]:
        """
        Calculate percent change from previous value for each data point.
        
        Returns list of formatted strings like "+5.2%", "-3.1%", or "" for first value.
        """
        changes = []
        for i, val in enumerate(values):
            if i == 0:
                changes.append("")  # No previous value
            else:
                prev = values[i - 1]
                if prev != 0:
                    pct = ((val - prev) / prev) * 100
                    if pct > 0:
                        changes.append(f"+{pct:.1f}%")
                    else:
                        changes.append(f"{pct:.1f}%")
                else:
                    changes.append("")
        return changes
    
    def _check_abnormal_values(self, record_type: str, values: List[float]) -> List[bool]:
        """
        Check which values are outside the normal reference range.
        
        Returns list of booleans - True if abnormal, False if normal or unknown.
        """
        normalized = record_type.lower()
        
        if normalized not in NORMAL_RANGES:
            return [False] * len(values)
        
        min_normal, max_normal, _ = NORMAL_RANGES[normalized]
        
        return [
            not (min_normal <= val <= max_normal)
            for val in values
        ]
    
    def _get_default_unit(self, record_type: str) -> str:
        """Get default unit for a metric type."""
        return DEFAULT_UNITS.get(record_type.lower(), '')
    
    def _get_metric_color(self, record_type: str) -> str:
        """Get semantic color for a metric type."""
        normalized = record_type.lower()
        
        # Direct lookup
        if normalized in METRIC_COLORS:
            return METRIC_COLORS[normalized]
        
        # Partial match for variations
        for key, color in METRIC_COLORS.items():
            if key in normalized or normalized in key:
                return color
        
        # Default to a distinguishable gray
        return '#546E7A'  # Blue-gray
    
    def _get_category(self, record_type: str) -> str:
        """Determine the clinical category for a metric."""
        normalized = record_type.lower()
        
        kidney_keywords = ['creatinine', 'urea', 'bun', 'egfr']
        sugar_keywords = ['sugar', 'glucose', 'hba1c', 'blood sugar']
        electrolyte_keywords = ['sodium', 'potassium', 'chloride', 'calcium', 'phosphorus', 'magnesium']
        blood_keywords = ['haemoglobin', 'hemoglobin', 'hematocrit', 'rbc', 'wbc', 'platelets']
        
        if any(kw in normalized for kw in kidney_keywords):
            return 'kidney'
        elif any(kw in normalized for kw in sugar_keywords):
            return 'sugar'
        elif any(kw in normalized for kw in electrolyte_keywords):
            return 'electrolyte'
        elif any(kw in normalized for kw in blood_keywords):
            return 'blood'
        else:
            return 'other'
    
    def _create_trace(
        self, 
        record_type: str, 
        trace_data: Dict[str, Any],
        is_visible: bool
    ) -> go.Scatter:
        """Create a Plotly trace with semantic styling and abnormal value highlighting."""
        base_color = self._get_metric_color(record_type)
        unit = trace_data['unit']
        values = trace_data['values']
        is_abnormal = trace_data.get('is_abnormal', [False] * len(values))
        percent_changes = trace_data.get('percent_changes', [''] * len(values))
        
        # Create trace name with unit
        trace_name = f"{record_type} ({unit})" if unit else record_type
        
        # Create per-point marker colors (red border for abnormal values)
        marker_colors = []
        marker_line_colors = []
        marker_symbols = []
        
        for abnormal in is_abnormal:
            if abnormal:
                marker_colors.append('#FFEBEE')  # Light red fill for abnormal
                marker_line_colors.append('#E53935')  # Red border for abnormal
                marker_symbols.append('circle')
            else:
                marker_colors.append(base_color)
                marker_line_colors.append('white')
                marker_symbols.append('circle')
        
        # Build custom data for hover (combine date and percent change)
        custom_data = []
        for i, (date, pct) in enumerate(zip(trace_data['formatted_dates'], percent_changes)):
            if pct:
                custom_data.append(f"{date}<br>Change: {pct}")
            else:
                custom_data.append(date)
        
        # Build custom hover template
        # Note: customdata now includes date + optional percent change
        hovertemplate = (
            f"<b>{record_type}</b><br>"
            "%{customdata}<br>"  # Formatted date + percent change
            f"Value: %{{y:.2f}} {unit}"
            "<extra></extra>"
        )
        
        return go.Scatter(
            x=trace_data['timestamps'],
            y=values,
            mode='lines+markers',
            name=trace_name,
            visible=True if is_visible else "legendonly",
            showlegend=True,
            line=dict(
                width=3.5,           # Thicker for mobile visibility
                shape='linear',
                color=base_color,
            ),
            marker=dict(
                size=12,             # Larger markers for touch
                color=marker_colors,
                line=dict(
                    width=2.5,
                    color=marker_line_colors
                ),
                symbol=marker_symbols,
            ),
            connectgaps=True,
            customdata=custom_data,
            hovertemplate=hovertemplate,
        )
    
    def _add_reference_band(
        self, 
        fig: go.Figure, 
        metric: str, 
        date_range: Tuple[datetime, datetime],
        all_values: List[float]
    ) -> None:
        """
        Add a subtle reference range band for a metric.
        
        These bands are purely informational and show general adult reference ranges.
        """
        normalized = metric.lower()
        
        if normalized not in NORMAL_RANGES:
            return
        
        min_normal, max_normal, _ = NORMAL_RANGES[normalized]
        category = self._get_category(metric)
        fill_color = RANGE_BAND_COLORS.get(category, RANGE_BAND_COLORS['other'])
        
        # Extend date range slightly for visual padding
        from datetime import timedelta
        x0 = date_range[0] - timedelta(days=7)
        x1 = date_range[1] + timedelta(days=7)
        
        # Add shaded rectangle for normal range
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=min_normal,
            y1=max_normal,
            fillcolor=fill_color,
            line=dict(width=0),
            layer="below",
            name=f"{metric} normal range",
        )
        
        # Add subtle annotation for the range (positioned at the edge)
        # Only add if the range is meaningful relative to the data
        if all_values:
            data_min = min(all_values)
            data_max = max(all_values)
            # Only annotate if the range is visible in the current view
            if data_min <= max_normal * 1.5 and data_max >= min_normal * 0.5:
                fig.add_annotation(
                    x=x1,
                    y=(min_normal + max_normal) / 2,
                    text=f"Normal: {min_normal}-{max_normal}",
                    showarrow=False,
                    font=dict(size=10, color='rgba(0,0,0,0.4)'),
                    xanchor='left',
                    xshift=5,
                )
    
    def _apply_layout(
        self, 
        fig: go.Figure, 
        patient_name: str,
        date_range: Tuple[datetime, datetime]
    ) -> None:
        """Apply mobile-optimized layout configuration."""
        fig.update_layout(
            # Title
            title=dict(
                text=f"<b>Health Records</b><br><sup>{patient_name}</sup>",
                font=dict(size=20, color='#212121'),
                x=0.5,
                xanchor='center',
                y=0.95,
            ),
            
            # X-axis (dates)
            xaxis=dict(
                title=dict(
                    text="Date",
                    font=dict(size=14, color='#424242'),
                    standoff=10,
                ),
                type="date",
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(0,0,0,0.08)',
                tickfont=dict(size=12, color='#616161'),
                tickformat='%b %d',  # "Nov 19" format
                dtick='M1',  # Monthly ticks
                showline=True,
                linewidth=1,
                linecolor='rgba(0,0,0,0.2)',
            ),
            
            # Y-axis (values)
            yaxis=dict(
                title=dict(
                    text="Value",
                    font=dict(size=14, color='#424242'),
                    standoff=10,
                ),
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(0,0,0,0.08)',
                tickfont=dict(size=12, color='#616161'),
                showline=True,
                linewidth=1,
                linecolor='rgba(0,0,0,0.2)',
                zeroline=False,
            ),
            
            # Hover mode
            hovermode='x unified',
            
            # Legend - optimized for mobile touch
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.12,
                xanchor="center",
                x=0.5,
                font=dict(size=13, color='#424242'),
                itemclick="toggle",
                itemdoubleclick="toggleothers",
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor="rgba(0,0,0,0.15)",
                borderwidth=1,
                itemsizing='constant',
                tracegroupgap=8,
            ),
            
            # Sizing - taller for mobile scrolling
            height=680,
            autosize=True,
            margin=dict(
                l=55,
                r=55,
                t=100,
                b=160,  # Extra space for legend + helper text
            ),
            
            # Template and colors
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            
            # Interaction
            dragmode='pan',
            
            # Hover styling
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="rgba(0,0,0,0.2)",
                font=dict(size=13, color='#212121'),
                namelength=-1,  # Show full name
            ),
        )
        
        # Add legend helper text
        fig.add_annotation(
            text="<i>Tap legend items to show/hide metrics • Red-bordered points are outside normal range</i>",
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0.22,
            showarrow=False,
            font=dict(size=11, color='#9E9E9E'),
            xanchor='center',
        )
    
    def _get_mobile_config(self) -> Dict[str, Any]:
        """
        Get Plotly configuration optimized for mobile/touch devices.
        """
        return {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': [
                'lasso2d', 
                'select2d',
                'autoScale2d',
            ],
            'responsive': True,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'health_records',
                'height': 800,
                'width': 1200,
                'scale': 2,  # Higher resolution for sharing
            },
            'scrollZoom': True,
            'doubleClick': 'reset',
            'showTips': True,
        }
    
    def _inject_mobile_css(self, html_content: str) -> str:
        """Inject mobile-responsive CSS into the HTML."""
        mobile_css = """
        <style>
            * {
                box-sizing: border-box;
            }
            body {
                margin: 0;
                padding: 8px;
                background-color: #FAFAFA;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            #health-graph {
                width: 100% !important;
                max-width: 100%;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                background: white;
            }
            .js-plotly-plot {
                width: 100% !important;
                max-width: 100%;
            }
            /* Improve legend touch targets */
            .legend .traces .legendtoggle {
                min-height: 44px !important;
            }
            /* Mobile-specific adjustments */
            @media (max-width: 768px) {
                body {
                    padding: 4px;
                }
                #health-graph {
                    border-radius: 8px;
                }
                /* Hide mode bar on very small screens for cleaner look */
                .plotly .modebar {
                    display: none !important;
                }
            }
            @media (max-width: 480px) {
                body {
                    padding: 2px;
                }
            }
            /* Ensure proper touch handling */
            @media (pointer: coarse) {
                .legend .traces {
                    cursor: pointer;
                }
            }
        </style>
        """
        return html_content.replace('<body>', f'<body>{mobile_css}')
    
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
            
            logger.warning(f"Could not parse value '{value_str}', using 0.0")
            return 0.0

