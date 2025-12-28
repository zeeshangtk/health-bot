"""
Service layer for generating health record visualization graphs.

Features:
- Unified metric registry (single source of truth for colors, ranges, units, axis)
- Dual Y-axis support for metrics with different scales
- Blood pressure high-low chart visualization
- Semantic color coding by category
- Reference range bands (informational only)
- Abnormal value highlighting (red borders)
- Touch-friendly markers and horizontal legend
- Educational metric descriptions in tooltips
- Summary panel with latest readings
- Date range filters and slider
- Spline curves for smooth visualization
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

import plotly.graph_objects as go
import plotly.io as pio

from api.schemas import HealthRecordResponse

logger = logging.getLogger(__name__)


# =============================================================================
# UNIFIED METRIC REGISTRY
# Single source of truth for all metric configuration
# =============================================================================
METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Kidney Function - Blues (y2 axis for small decimal values)
    'creatinine': {
        'color': '#1E88E5',
        'range': (0.6, 1.2),
        'unit': 'mg/dl',
        'axis': 'y2',
        'category': 'kidney',
        'description': 'Waste product filtered by kidneys',
    },
    'serum creatinine': {
        'color': '#1E88E5',
        'range': (0.6, 1.2),
        'unit': 'mg/dl',
        'axis': 'y2',
        'category': 'kidney',
        'description': 'Waste product filtered by kidneys',
    },
    'blood urea': {
        'color': '#1565C0',
        'range': (15.0, 45.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'kidney',
        'description': 'Protein breakdown product',
    },
    'serum urea': {
        'color': '#1565C0',
        'range': (15.0, 45.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'kidney',
        'description': 'Protein breakdown product',
    },
    'blood urea nitrogen': {
        'color': '#0D47A1',
        'range': (7.0, 20.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'kidney',
        'description': 'Nitrogen from protein breakdown',
    },
    'bun': {
        'color': '#0D47A1',
        'range': (7.0, 20.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'kidney',
        'description': 'Nitrogen from protein breakdown',
    },

    # Blood Sugar - Greens
    'random blood sugar': {
        'color': '#43A047',
        'range': (70.0, 140.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'sugar',
        'description': 'Glucose level at any time',
    },
    'fasting blood sugar': {
        'color': '#2E7D32',
        'range': (70.0, 100.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'sugar',
        'description': 'Glucose after 8+ hours fasting',
    },
    'blood sugar': {
        'color': '#66BB6A',
        'range': (70.0, 140.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'sugar',
        'description': 'Current glucose level',
    },
    'glucose': {
        'color': '#4CAF50',
        'range': (70.0, 140.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'sugar',
        'description': 'Blood sugar level',
    },
    'hba1c': {
        'color': '#1B5E20',
        'range': (4.0, 5.6),
        'unit': '%',
        'axis': 'y2',
        'category': 'sugar',
        'description': 'Average blood sugar over 2-3 months',
    },

    # Electrolytes - Purples
    'sodium': {
        'color': '#8E24AA',
        'range': (136.0, 145.0),
        'unit': 'mMol/L',
        'axis': 'y1',
        'category': 'electrolyte',
        'description': 'Fluid balance & nerve function',
    },
    'potassium': {
        'color': '#AB47BC',
        'range': (3.5, 5.0),
        'unit': 'mMol/L',
        'axis': 'y2',
        'category': 'electrolyte',
        'description': 'Heart & muscle function',
    },
    'chloride': {
        'color': '#7B1FA2',
        'range': (98.0, 106.0),
        'unit': 'mMol/L',
        'axis': 'y1',
        'category': 'electrolyte',
        'description': 'Fluid balance & digestion',
    },
    'calcium': {
        'color': '#BA68C8',
        'range': (8.5, 10.5),
        'unit': 'mg/dl',
        'axis': 'y2',
        'category': 'electrolyte',
        'description': 'Bone health & muscle function',
    },

    # Blood/Hematology - Reds
    'haemoglobin': {
        'color': '#E53935',
        'range': (12.0, 17.5),
        'unit': 'g/dl',
        'axis': 'y1',
        'category': 'blood',
        'description': 'Oxygen-carrying capacity',
    },
    'hemoglobin': {
        'color': '#E53935',
        'range': (12.0, 17.5),
        'unit': 'g/dl',
        'axis': 'y1',
        'category': 'blood',
        'description': 'Oxygen-carrying capacity',
    },
    'hematocrit': {
        'color': '#C62828',
        'range': (36.0, 50.0),
        'unit': '%',
        'axis': 'y1',
        'category': 'blood',
        'description': 'Red blood cell percentage',
    },
    'platelets': {
        'color': '#D32F2F',
        'range': (150.0, 450.0),
        'unit': 'k/µL',
        'axis': 'y1',
        'category': 'blood',
        'description': 'Blood clotting cells',
    },

    # Liver Function - Oranges
    'bilirubin': {
        'color': '#FB8C00',
        'range': (0.1, 1.2),
        'unit': 'mg/dl',
        'axis': 'y2',
        'category': 'liver',
        'description': 'Liver processing indicator',
    },
    'sgpt': {
        'color': '#F57C00',
        'range': (7.0, 56.0),
        'unit': 'U/L',
        'axis': 'y1',
        'category': 'liver',
        'description': 'Liver enzyme (ALT)',
    },
    'alt': {
        'color': '#F57C00',
        'range': (7.0, 56.0),
        'unit': 'U/L',
        'axis': 'y1',
        'category': 'liver',
        'description': 'Liver cell health marker',
    },
    'sgot': {
        'color': '#EF6C00',
        'range': (10.0, 40.0),
        'unit': 'U/L',
        'axis': 'y1',
        'category': 'liver',
        'description': 'Liver enzyme (AST)',
    },
    'ast': {
        'color': '#EF6C00',
        'range': (10.0, 40.0),
        'unit': 'U/L',
        'axis': 'y1',
        'category': 'liver',
        'description': 'Liver & heart enzyme',
    },

    # Lipids - Teals
    'cholesterol': {
        'color': '#00897B',
        'range': (0.0, 200.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'lipid',
        'description': 'Total blood fats',
    },
    'triglycerides': {
        'color': '#00796B',
        'range': (0.0, 150.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'lipid',
        'description': 'Fat from food & body',
    },
    'hdl': {
        'color': '#26A69A',
        'range': (40.0, 60.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'lipid',
        'description': 'Good cholesterol',
    },
    'ldl': {
        'color': '#004D40',
        'range': (0.0, 100.0),
        'unit': 'mg/dl',
        'axis': 'y1',
        'category': 'lipid',
        'description': 'Bad cholesterol',
    },

    # Other - Grays
    'uric acid': {
        'color': '#757575',
        'range': (2.4, 7.0),
        'unit': 'mg/dl',
        'axis': 'y2',
        'category': 'other',
        'description': 'Purine breakdown product',
    },
}

# Default metric info for unknown metrics
DEFAULT_METRIC = {
    'color': '#546E7A',
    'range': None,
    'unit': '',
    'axis': 'y1',
    'category': 'other',
    'description': '',
}

# Reference band colors by category
RANGE_BAND_COLORS = {
    'kidney': 'rgba(30, 136, 229, 0.10)',
    'sugar': 'rgba(67, 160, 71, 0.10)',
    'electrolyte': 'rgba(142, 36, 170, 0.10)',
    'blood': 'rgba(229, 57, 53, 0.10)',
    'liver': 'rgba(251, 140, 0, 0.10)',
    'lipid': 'rgba(0, 137, 123, 0.10)',
    'other': 'rgba(117, 117, 117, 0.08)',
}

# Clinically important metrics to show by default
DEFAULT_VISIBLE_METRICS = [
    'creatinine', 'serum creatinine', 'blood urea',
    'random blood sugar', 'haemoglobin', 'hemoglobin',
]


class GraphService:
    """Service for generating enhanced health record graphs with dual Y-axis support."""

    def generate_html_graph(self, records: List[HealthRecordResponse], patient_name: str) -> str:
        """Generate complete HTML with interactive Plotly graph."""
        if not records:
            return self._generate_empty_graph(patient_name)

        # Group by metric type
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            records_by_type[record.record_type.lower()].append(record)

        visible_metrics = self._get_default_visible_metrics(list(records_by_type.keys()))
        fig = go.Figure()
        all_dates: List[datetime] = []

        # Handle Blood Pressure specially (systolic/diastolic as range chart)
        if 'systolic' in records_by_type and 'diastolic' in records_by_type:
            self._add_blood_pressure_trace(fig, records_by_type)
            all_dates.extend([datetime.fromisoformat(r.timestamp) for r in records_by_type['systolic']])
            del records_by_type['systolic']
            del records_by_type['diastolic']

        # Add standard traces
        for record_type, type_records in records_by_type.items():
            trace_data = self._prepare_trace_data(record_type, type_records)
            all_dates.extend(trace_data['timestamps'])
            is_visible = record_type in visible_metrics
            fig.add_trace(self._create_trace(record_type, trace_data, is_visible))

        # Date range for reference bands
        if all_dates:
            date_range = (min(all_dates), max(all_dates))
        else:
            now = datetime.now()
            date_range = (now, now)

        # Add reference bands for metrics with known ranges
        for record_type in records_by_type:
            self._add_reference_band(fig, record_type, date_range)

        # Apply layout and add summary
        self._apply_layout(fig, patient_name)
        self._add_summary_panel(fig, records_by_type, date_range[1])

        # Disclaimer
        fig.add_annotation(
            text="ℹ️ Shaded bands show typical adult reference ranges (informational only — not medical advice)",
            xref="paper", yref="paper",
            x=0.5, y=-0.30,
            showarrow=False,
            font=dict(size=9, color="#757575"),
            xanchor="center"
        )

        html_content = pio.to_html(
            fig,
            include_plotlyjs='cdn',
            config=self._get_mobile_config(),
            div_id="health-graph"
        )

        return self._inject_mobile_css(html_content)

    # =========================================================================
    # Helper methods
    # =========================================================================

    def _get_metric_info(self, record_type: str) -> Dict[str, Any]:
        """Get metric info from registry, with fallback for unknown metrics."""
        normalized = record_type.lower()
        if normalized in METRIC_REGISTRY:
            return METRIC_REGISTRY[normalized]
        # Partial match
        for key, info in METRIC_REGISTRY.items():
            if key in normalized or normalized in key:
                return info
        return DEFAULT_METRIC

    def _generate_empty_graph(self, patient_name: str) -> str:
        """Generate styled placeholder graph when no records exist."""
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text=f"<b>Health Trends</b><br><sup>{patient_name}</sup>",
                font=dict(size=20),
                x=0.5, xanchor='center'
            ),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=450,
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            annotations=[
                dict(text='📊', xref='paper', yref='paper', x=0.5, y=0.6,
                     showarrow=False, font=dict(size=48)),
                dict(text='<b>No health records yet</b>', xref='paper', yref='paper',
                     x=0.5, y=0.42, showarrow=False, font=dict(size=18, color='#424242')),
                dict(text='Upload a lab report to see your health trends',
                     xref='paper', yref='paper', x=0.5, y=0.32,
                     showarrow=False, font=dict(size=14, color='#757575')),
            ]
        )
        html = pio.to_html(fig, include_plotlyjs='cdn', config=self._get_mobile_config())
        return self._inject_mobile_css(html)

    def _get_default_visible_metrics(self, available_metrics: List[str]) -> List[str]:
        """Determine which metrics to show by default."""
        visible = []
        for priority in DEFAULT_VISIBLE_METRICS:
            if priority in available_metrics:
                visible.append(priority)
                if len(visible) >= 3:
                    break
        if len(visible) < 2:
            for m in available_metrics:
                if m not in visible:
                    visible.append(m)
                    if len(visible) >= 2:
                        break
        return visible

    def _prepare_trace_data(self, record_type: str, type_records: List[HealthRecordResponse]) -> Dict[str, Any]:
        """Prepare data for a trace with abnormal detection."""
        sorted_records = sorted(type_records, key=lambda x: x.timestamp)
        
        timestamps = []
        values = []
        for r in sorted_records:
            try:
                timestamps.append(datetime.fromisoformat(r.timestamp))
                values.append(self._parse_value(r.value))
            except (ValueError, AttributeError):
                continue

        metric_info = self._get_metric_info(record_type)
        unit = sorted_records[0].unit if sorted_records and sorted_records[0].unit else metric_info['unit']
        is_abnormal = self._check_abnormal_values(record_type, values)

        return {
            'timestamps': timestamps,
            'values': values,
            'unit': unit,
            'is_abnormal': is_abnormal,
        }

    def _parse_value(self, value_str: str) -> float:
        """Parse value string to float."""
        try:
            return float(value_str)
        except ValueError:
            if '/' in value_str:
                return float(value_str.split('/')[0].strip())
            match = re.search(r'(\d+\.?\d*)', str(value_str))
            if match:
                return float(match.group(1))
            logger.warning(f"Could not parse value '{value_str}'")
            return 0.0

    def _check_abnormal_values(self, record_type: str, values: List[float]) -> List[bool]:
        """Check which values are outside normal range."""
        metric_info = self._get_metric_info(record_type)
        if metric_info['range'] is None:
            return [False] * len(values)
        low, high = metric_info['range']
        return [not (low <= v <= high) for v in values]

    def _get_trend_indicator(self, values: List[float]) -> str:
        """Get trend arrow based on last two values."""
        if len(values) < 2 or values[-2] == 0:
            return ""
        pct = ((values[-1] - values[-2]) / values[-2]) * 100
        if pct > 5:
            return " ↑"
        elif pct < -5:
            return " ↓"
        return " →"

    def _add_blood_pressure_trace(self, fig: go.Figure, records_by_type: Dict) -> None:
        """Add specialized blood pressure high-low chart."""
        sys_records = sorted(records_by_type['systolic'], key=lambda x: x.timestamp)
        dia_records = sorted(records_by_type['diastolic'], key=lambda x: x.timestamp)

        dates = [datetime.fromisoformat(r.timestamp) for r in sys_records]
        sys_vals = [self._parse_value(r.value) for r in sys_records]
        dia_vals = [self._parse_value(r.value) for r in dia_records]

        # Systolic trace
        fig.add_trace(go.Scatter(
            x=dates, y=sys_vals,
            name="Systolic ↑",
            mode='lines+markers',
            line=dict(color='#37474F', width=3, shape='spline'),
            marker=dict(size=10, color='#37474F', line=dict(width=2, color='white')),
            hovertemplate="<b>Systolic</b><br>%{x|%b %d, %Y}<br>Value: %{y} mmHg<extra></extra>",
        ))

        # Diastolic trace with fill to systolic
        fig.add_trace(go.Scatter(
            x=dates, y=dia_vals,
            name="Diastolic ↓",
            mode='lines+markers',
            line=dict(color='#78909C', width=3, shape='spline'),
            marker=dict(size=10, color='#78909C', line=dict(width=2, color='white')),
            fill='tonexty',
            fillcolor='rgba(55, 71, 79, 0.15)',
            hovertemplate="<b>Diastolic</b><br>%{x|%b %d, %Y}<br>Value: %{y} mmHg<extra></extra>",
        ))

    def _create_trace(self, record_type: str, trace_data: Dict[str, Any], is_visible: bool) -> go.Scatter:
        """Create a trace with spline curves, value labels, and abnormal highlighting."""
        metric_info = self._get_metric_info(record_type)
        color = metric_info['color']
        unit = trace_data['unit']
        values = trace_data['values']
        is_abnormal = trace_data['is_abnormal']
        description = metric_info['description']
        trend = self._get_trend_indicator(values)

        # Trace name with trend
        name = f"{record_type.title()}{trend}"
        if unit:
            name += f" ({unit})"

        # Abnormal highlighting: red thick border
        line_widths = [4 if a else 2 for a in is_abnormal]
        line_colors = ['#E53935' if a else 'white' for a in is_abnormal]

        # Value labels (smart formatting)
        text_labels = []
        for val in values:
            if val >= 100:
                text_labels.append(f"{val:.0f}")
            elif val >= 10:
                text_labels.append(f"{val:.1f}")
            else:
                text_labels.append(f"{val:.2f}")

        # Hover template with description
        desc_line = f"<i>{description}</i><br>" if description else ""
        hovertemplate = (
            f"<b>{record_type.title()}</b><br>"
            f"{desc_line}"
            "%{x|%b %d, %Y}<br>"
            f"Value: %{{y:.2f}} {unit}"
            "<extra></extra>"
        )

        return go.Scatter(
            x=trace_data['timestamps'],
            y=values,
            yaxis=metric_info['axis'],
            name=name,
            visible=True if is_visible else "legendonly",
            mode='lines+markers+text',
            line=dict(width=3.5, color=color, shape='spline'),
            marker=dict(
                size=12,
                color=color,
                line=dict(width=line_widths, color=line_colors)
            ),
            text=text_labels,
            textposition='top center',
            textfont=dict(size=10, color='#616161'),
            connectgaps=True,
            hovertemplate=hovertemplate,
        )

    def _add_reference_band(self, fig: go.Figure, record_type: str, date_range: Tuple[datetime, datetime]) -> None:
        """Add subtle reference range band for a metric."""
        metric_info = self._get_metric_info(record_type)
        if metric_info['range'] is None:
            return

        low, high = metric_info['range']
        category = metric_info['category']
        fill_color = RANGE_BAND_COLORS.get(category, RANGE_BAND_COLORS['other'])

        x0 = date_range[0] - timedelta(days=7)
        x1 = date_range[1] + timedelta(days=7)

        fig.add_shape(
            type="rect",
            x0=x0, x1=x1,
            y0=low, y1=high,
            yref=metric_info['axis'],
            fillcolor=fill_color,
            line=dict(width=0),
            layer="below",
        )

    def _apply_layout(self, fig: go.Figure, patient_name: str) -> None:
        """Apply layout with dual Y-axis support."""
        fig.update_layout(
            title=dict(
                text=f"<b>Health Trends</b><br><sup>{patient_name}</sup>",
                font=dict(size=20),
                x=0.5, xanchor="center"
            ),
            xaxis=dict(
                title="Date",
                type="date",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.08)',
                tickformat='%b %d',
                rangeselector=dict(
                    buttons=[
                        dict(count=1, label="1M", step="month", stepmode="backward"),
                        dict(count=3, label="3M", step="month", stepmode="backward"),
                        dict(count=6, label="6M", step="month", stepmode="backward"),
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(step="all", label="All"),
                    ],
                    bgcolor='rgba(255,255,255,0.95)',
                    activecolor='#E3F2FD',
                ),
                rangeslider=dict(visible=True, thickness=0.05),
            ),
            # Primary Y-axis (left) for larger values
            yaxis=dict(
                title="Primary Metrics",
                side="left",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.08)',
            ),
            # Secondary Y-axis (right) for small decimal values
            yaxis2=dict(
                title="Micro Metrics",
                side="right",
                overlaying="y",
                showgrid=False,
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                x=0.5, xanchor="center",
                y=-0.18, yanchor="top",
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor="rgba(0,0,0,0.15)",
                borderwidth=1,
            ),
            height=750,
            margin=dict(l=60, r=60, t=100, b=200),
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            dragmode='pan',
            hoverlabel=dict(bgcolor="white", font_size=13),
        )

        fig.add_annotation(
            text="<i>Tap legend to show/hide • Red borders = outside typical range • Right axis for small values</i>",
            xref="paper", yref="paper",
            x=0.5, y=-0.26,
            showarrow=False,
            font=dict(size=10, color='#9E9E9E'),
            xanchor='center'
        )

    def _add_summary_panel(self, fig: go.Figure, records_by_type: Dict, latest_date: datetime) -> None:
        """Add summary panel with latest readings."""
        priority = ['creatinine', 'serum creatinine', 'blood urea', 'random blood sugar',
                    'haemoglobin', 'hemoglobin', 'sodium', 'potassium']
        
        sorted_metrics = []
        for p in priority:
            for m in records_by_type:
                if m == p and m not in sorted_metrics:
                    sorted_metrics.append(m)
        for m in records_by_type:
            if m not in sorted_metrics:
                sorted_metrics.append(m)

        items = []
        for metric in sorted_metrics[:5]:
            records = records_by_type[metric]
            latest = max(records, key=lambda r: r.timestamp)
            value = self._parse_value(latest.value)
            metric_info = self._get_metric_info(metric)
            unit = latest.unit or metric_info['unit']

            # Status icon
            if metric_info['range']:
                low, high = metric_info['range']
                icon = "✓" if low <= value <= high else "⚠️"
            else:
                icon = "✓"

            # Format value
            if value >= 100:
                val_str = f"{value:.0f}"
            elif value >= 10:
                val_str = f"{value:.1f}"
            else:
                val_str = f"{value:.2f}"

            items.append(f"{icon} {metric.title()}: {val_str} {unit}")

        if not items:
            return

        summary_text = f"<b>Latest ({latest_date.strftime('%b %d, %Y')})</b><br>" + "<br>".join(items)
        fig.add_annotation(
            text=summary_text,
            xref="paper", yref="paper",
            x=1.0, y=1.0,
            xanchor='right', yanchor='top',
            showarrow=False,
            font=dict(size=11),
            align='left',
            bgcolor='rgba(255,255,255,0.95)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1,
            borderpad=8,
        )

    def _get_mobile_config(self) -> Dict[str, Any]:
        """Mobile-optimized Plotly config."""
        return {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
            'responsive': True,
            'scrollZoom': True,
            'doubleClick': 'reset',
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'health_records',
                'height': 800,
                'width': 1200,
                'scale': 2
            },
        }

    def _inject_mobile_css(self, html_content: str) -> str:
        """Inject mobile-responsive CSS."""
        mobile_css = """
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                padding: 8px;
                background: #FAFAFA;
                font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            #health-graph {
                width: 100% !important;
                max-width: 100%;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                background: white;
            }
            .js-plotly-plot { width: 100% !important; }
            .legend .traces { cursor: pointer; }
            @media (max-width: 768px) {
                body { padding: 4px; }
                #health-graph { border-radius: 8px; }
                .modebar { display: none !important; }
            }
            @media (max-width: 480px) {
                body { padding: 2px; }
                .legend .legendtext { font-size: 10px !important; }
            }
        </style>
        """
        return html_content.replace('<body>', f'<body>{mobile_css}')
