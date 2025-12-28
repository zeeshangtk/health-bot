"""
Service layer for generating health record visualization graphs.

This module provides a mobile-optimized, clinically-informed Plotly graph 
generator for health records. Features include:
- Semantic color coding by metric category (kidney, sugar, electrolytes, etc.)
- Subtle reference range bands for key metrics (informational only)
- Touch-friendly markers and vertical legend optimized for Telegram/mobile
- Color-blind friendly palette
- Clean, formatted hover tooltips with educational descriptions
- Abnormal value highlighting (bold red border on markers)
- Latest readings summary panel
- Clear informational disclaimer
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
# CONFIGURATION: Semantic Colors, Reference Ranges, Units, etc.
# =============================================================================

# Color-blind friendly palette organized by clinical category
METRIC_COLORS: Dict[str, str] = {
    # Kidney Function - Blues
    'creatinine': '#1E88E5',
    'serum creatinine': '#1E88E5',
    'blood urea': '#1565C0',
    'serum urea': '#1565C0',
    'blood urea nitrogen': '#0D47A1',
    'bun': '#0D47A1',
    'egfr': '#42A5F5',

    # Blood Sugar - Greens
    'random blood sugar': '#43A047',
    'fasting blood sugar': '#2E7D32',
    'blood sugar': '#66BB6A',
    'hba1c': '#1B5E20',
    'glucose': '#4CAF50',

    # Electrolytes - Purples
    'sodium': '#8E24AA',
    'potassium': '#AB47BC',
    'chloride': '#7B1FA2',
    'calcium': '#BA68C8',
    'phosphorus': '#6A1B9A',
    'magnesium': '#CE93D8',

    # Blood/Hematology - Reds
    'haemoglobin': '#E53935',
    'hemoglobin': '#E53935',
    'hematocrit': '#C62828',
    'rbc': '#EF5350',
    'wbc': '#F44336',
    'platelets': '#D32F2F',

    # Liver Function - Oranges
    'bilirubin': '#FB8C00',
    'sgpt': '#F57C00',
    'alt': '#F57C00',
    'sgot': '#EF6C00',
    'ast': '#EF6C00',
    'alkaline phosphatase': '#FF9800',

    # Lipids - Teals
    'cholesterol': '#00897B',
    'triglycerides': '#00796B',
    'hdl': '#26A69A',
    'ldl': '#004D40',

    # Other - Grays
    'uric acid': '#757575',
    'protein': '#616161',
    'albumin': '#9E9E9E',
}

# General adult reference ranges (informational only)
NORMAL_RANGES: Dict[str, Tuple[float, float, str]] = {
    'creatinine': (0.6, 1.2, 'mg/dl'),
    'serum creatinine': (0.6, 1.2, 'mg/dl'),
    'blood urea': (15.0, 45.0, 'mg/dl'),
    'serum urea': (15.0, 45.0, 'mg/dl'),
    'blood urea nitrogen': (7.0, 20.0, 'mg/dl'),
    'bun': (7.0, 20.0, 'mg/dl'),
    'random blood sugar': (70.0, 140.0, 'mg/dl'),
    'fasting blood sugar': (70.0, 100.0, 'mg/dl'),
    'blood sugar': (70.0, 140.0, 'mg/dl'),
    'hba1c': (4.0, 5.6, '%'),
    'sodium': (136.0, 145.0, 'mMol/L'),
    'potassium': (3.5, 5.0, 'mMol/L'),
    'chloride': (98.0, 106.0, 'mMol/L'),
    'calcium': (8.5, 10.5, 'mg/dl'),
    'haemoglobin': (12.0, 17.5, 'g/dl'),
    'hemoglobin': (12.0, 17.5, 'g/dl'),
    'uric acid': (2.4, 7.0, 'mg/dl'),
}

# Fallback units
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

# Clinically important metrics to show by default (max 3)
DEFAULT_VISIBLE_METRICS: List[str] = [
    'creatinine',
    'serum creatinine',
    'blood urea',
    'random blood sugar',
    'haemoglobin',
    'hemoglobin',
]

# Subtle reference band colors by category
RANGE_BAND_COLORS: Dict[str, str] = {
    'kidney': 'rgba(30, 136, 229, 0.12)',
    'sugar': 'rgba(67, 160, 71, 0.12)',
    'electrolyte': 'rgba(142, 36, 170, 0.12)',
    'blood': 'rgba(229, 57, 53, 0.12)',
    'liver': 'rgba(251, 140, 0, 0.12)',
    'lipid': 'rgba(0, 137, 123, 0.12)',
    'other': 'rgba(117, 117, 117, 0.12)',
}

# Patient-friendly metric descriptions
METRIC_DESCRIPTIONS: Dict[str, str] = {
    'creatinine': 'Waste product filtered by kidneys',
    'serum creatinine': 'Waste product filtered by kidneys',
    'blood urea': 'Protein breakdown product',
    'serum urea': 'Protein breakdown product',
    'blood urea nitrogen': 'Nitrogen from protein breakdown',
    'bun': 'Nitrogen from protein breakdown',
    'random blood sugar': 'Glucose level at any time',
    'fasting blood sugar': 'Glucose after 8+ hours fasting',
    'blood sugar': 'Current glucose level',
    'glucose': 'Blood sugar level',
    'hba1c': 'Average blood sugar over 2-3 months',
    'sodium': 'Fluid balance & nerve function',
    'potassium': 'Heart & muscle function',
    'chloride': 'Fluid balance & digestion',
    'calcium': 'Bone health & muscle function',
    'haemoglobin': 'Oxygen-carrying capacity',
    'hemoglobin': 'Oxygen-carrying capacity',
    'uric acid': 'Purine breakdown product',
}


class GraphService:
    """Service for generating enhanced health record graphs."""

    def generate_html_graph(self, records: List[HealthRecordResponse], patient_name: str) -> str:
        """Generate complete HTML with interactive Plotly graph."""
        if not records:
            return self._generate_empty_graph(patient_name)

        # Group by metric
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            records_by_type[record.record_type].append(record)

        available_metrics = list(records_by_type.keys())
        visible_metrics = self._get_default_visible_metrics(available_metrics)

        fig = go.Figure()
        date_range = self._get_date_range(records)

        # Add all traces
        for record_type, type_records in records_by_type.items():
            trace_data = self._prepare_trace_data(record_type, type_records)
            is_visible = record_type in visible_metrics
            fig.add_trace(self._create_trace(record_type, trace_data, is_visible))

        # Add reference bands for ALL metrics with ranges
        for record_type in records_by_type:
            if record_type.lower() in NORMAL_RANGES:
                self._add_reference_band(fig, record_type, date_range)

        # Layout and extras
        self._apply_layout(fig, patient_name)
        self._add_summary_panel(fig, records_by_type, date_range[1])

        # Disclaimer
        fig.add_annotation(
            text="ℹ️ Shaded bands show typical adult reference ranges (general information only — not medical advice)",
            xref="paper", yref="paper",
            x=0.5, y=-0.32,
            showarrow=False,
            font=dict(size=9, color="#757575"),
            xanchor="center", align="center"
        )

        html_content = pio.to_html(
            fig,
            include_plotlyjs='cdn',
            config=self._get_mobile_config(),
            div_id="health-graph"
        )

        return self._inject_mobile_css(html_content)

    # --------------------------------------------------------------------- #
    # Supporting methods
    # --------------------------------------------------------------------- #

    def _generate_empty_graph(self, patient_name: str) -> str:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text=f"<b>Health Records</b><br><sup>{patient_name}</sup>", font=dict(size=20), x=0.5, xanchor='center'),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=450,
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            annotations=[
                dict(text='📊', xref='paper', yref='paper', x=0.5, y=0.6, showarrow=False, font=dict(size=48)),
                dict(text='<b>No health records yet</b>', xref='paper', yref='paper', x=0.5, y=0.42, showarrow=False, font=dict(size=18, color='#424242')),
                dict(text='Upload a lab report to see trends', xref='paper', yref='paper', x=0.5, y=0.32, showarrow=False, font=dict(size=14, color='#757575')),
            ]
        )
        html = pio.to_html(fig, include_plotlyjs='cdn', config=self._get_mobile_config())
        return self._inject_mobile_css(html)

    def _get_default_visible_metrics(self, available_metrics: List[str]) -> List[str]:
        normalized = {m.lower(): m for m in available_metrics}
        visible = []
        for priority in DEFAULT_VISIBLE_METRICS:
            if priority in normalized:
                visible.append(normalized[priority])
                if len(visible) >= 3:
                    break
        if len(visible) < 2 and available_metrics:
            for m in available_metrics:
                if m not in visible:
                    visible.append(m)
                    if len(visible) >= 2:
                        break
        return visible

    def _get_date_range(self, records: List[HealthRecordResponse]) -> Tuple[datetime, datetime]:
        dates = []
        for r in records:
            try:
                dt = datetime.fromisoformat(r.timestamp)
                dates.append(dt)
            except (ValueError, AttributeError):
                continue
        if not dates:
            now = datetime.now()
            return now, now
        return min(dates), max(dates)

    def _prepare_trace_data(self, record_type: str, type_records: List[HealthRecordResponse]) -> Dict[str, Any]:
        records_with_dt = []
        for r in type_records:
            try:
                dt = datetime.fromisoformat(r.timestamp)
                records_with_dt.append((dt, r))
            except (ValueError, AttributeError):
                continue

        sorted_records = sorted(records_with_dt, key=lambda x: x[0])

        timestamps = [dt for dt, _ in sorted_records]
        values = [self._parse_value(r.value) for _, r in sorted_records]
        unit = (type_records[0].unit or self._get_default_unit(record_type)) if type_records else ''

        is_abnormal = self._check_abnormal_values(record_type, values)

        return {
            'timestamps': timestamps,
            'values': values,
            'unit': unit,
            'is_abnormal': is_abnormal,
        }

    def _parse_value(self, value_str: str) -> float:
        try:
            return float(value_str)
        except ValueError:
            if '/' in value_str:
                return float(value_str.split('/')[0].strip())
            match = re.search(r'(\d+\.?\d*)', value_str)
            if match:
                return float(match.group(1))
            logger.warning(f"Could not parse value '{value_str}'")
            return 0.0

    def _check_abnormal_values(self, record_type: str, values: List[float]) -> List[bool]:
        norm = record_type.lower()
        if norm not in NORMAL_RANGES:
            return [False] * len(values)
        low, high, _ = NORMAL_RANGES[norm]
        return [not (low <= v <= high) for v in values]

    def _get_default_unit(self, record_type: str) -> str:
        return DEFAULT_UNITS.get(record_type.lower(), '')

    def _get_metric_color(self, record_type: str) -> str:
        norm = record_type.lower()
        if norm in METRIC_COLORS:
            return METRIC_COLORS[norm]
        for key, color in METRIC_COLORS.items():
            if key in norm or norm in key:
                return color
        return '#546E7A'

    def _get_category(self, record_type: str) -> str:
        norm = record_type.lower()
        keyword_maps = {
            'kidney': ['creatinine', 'urea', 'bun', 'egfr'],
            'sugar': ['sugar', 'glucose', 'hba1c'],
            'electrolyte': ['sodium', 'potassium', 'chloride', 'calcium', 'phosphorus', 'magnesium'],
            'blood': ['haemoglobin', 'hemoglobin', 'hematocrit', 'rbc', 'wbc', 'platelets'],
            'liver': ['bilirubin', 'sgpt', 'alt', 'sgot', 'ast', 'alkaline phosphatase'],
            'lipid': ['cholesterol', 'triglycerides', 'hdl', 'ldl'],
        }
        for cat, keywords in keyword_maps.items():
            if any(k in norm for k in keywords):
                return cat
        return 'other'

    def _get_trend_indicator(self, values: List[float]) -> str:
        if len(values) < 2:
            return ""
        pct = ((values[-1] - values[-2]) / values[-2]) * 100 if values[-2] != 0 else 0
        if pct > 5:
            return " ↑"
        elif pct < -5:
            return " ↓"
        return " →"

    def _get_metric_description(self, record_type: str) -> str:
        norm = record_type.lower()
        if norm in METRIC_DESCRIPTIONS:
            return METRIC_DESCRIPTIONS[norm]
        for key, desc in METRIC_DESCRIPTIONS.items():
            if key in norm or norm in key:
                return desc
        return ""

    def _create_trace(self, record_type: str, trace_data: Dict[str, Any], is_visible: bool) -> go.Scatter:
        base_color = self._get_metric_color(record_type)
        unit = trace_data['unit']
        values = trace_data['values']
        is_abnormal = trace_data['is_abnormal']
        description = self._get_metric_description(record_type)
        trend = self._get_trend_indicator(values)

        name = f"{record_type}{trend}"
        if unit:
            name += f" ({unit})"

        # Red bold border only on abnormal points
        line_widths = [4 if a else 2 for a in is_abnormal]
        line_colors = ['#E53935' if a else 'white' for a in is_abnormal]

        # Text labels for data points (value displayed on chart)
        text_labels = []
        for val in values:
            if val >= 100:
                text_labels.append(f"{val:.0f}")
            elif val >= 10:
                text_labels.append(f"{val:.1f}")
            else:
                text_labels.append(f"{val:.2f}")

        desc_line = f"<i>{description}</i><br>" if description else ""
        hovertemplate = (
            f"<b>{record_type}</b><br>"
            f"{desc_line}"
            "%{x|%b %d, %Y}<br>"
            f"Value: %{{y:.2f}} {unit}"
            "<extra></extra>"
        )

        return go.Scatter(
            x=trace_data['timestamps'],
            y=values,
            mode='lines+markers+text',  # Added text mode for value labels
            name=name,
            visible=True if is_visible else "legendonly",
            line=dict(width=3.5, color=base_color),
            marker=dict(
                size=12,
                color=base_color,
                line=dict(width=line_widths, color=line_colors)
            ),
            text=text_labels,
            textposition='top center',
            textfont=dict(size=10, color='#616161'),
            connectgaps=True,
            hovertemplate=hovertemplate,
        )

    def _add_reference_band(self, fig: go.Figure, metric: str, date_range: Tuple[datetime, datetime]) -> None:
        norm = metric.lower()
        if norm not in NORMAL_RANGES:
            return
        low, high, _ = NORMAL_RANGES[norm]
        cat = self._get_category(metric)
        color = RANGE_BAND_COLORS.get(cat, RANGE_BAND_COLORS['other'])

        x0 = date_range[0] - timedelta(days=7)
        x1 = date_range[1] + timedelta(days=7)

        fig.add_shape(
            type="rect",
            x0=x0, x1=x1,
            y0=low, y1=high,
            fillcolor=color,
            line=dict(width=0),
            layer="below",
        )

    def _apply_layout(self, fig: go.Figure, patient_name: str) -> None:
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
            yaxis=dict(
                title="Value",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.08)',
            ),
            hovermode='x unified',
            # Legend: horizontal at bottom (better for mobile), wraps naturally
            legend=dict(
                orientation="h",
                x=0.5, xanchor="center",
                y=-0.15, yanchor="top",
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor="rgba(0,0,0,0.15)",
                borderwidth=1,
                itemclick="toggle",
                itemdoubleclick="toggleothers",
            ),
            height=720,
            margin=dict(l=60, r=40, t=100, b=180),  # More bottom space for legend
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            dragmode='pan',
            hoverlabel=dict(bgcolor="white", font_size=13),
        )

        fig.add_annotation(
            text="<i>Tap legend to show/hide • Red borders = outside typical range</i>",
            xref="paper", yref="paper",
            x=0.5, y=-0.25,
            showarrow=False,
            font=dict(size=10, color='#9E9E9E'),
            xanchor='center'
        )

    def _add_summary_panel(self, fig: go.Figure, records_by_type: Dict[str, List[HealthRecordResponse]], latest_date: datetime) -> None:
        priority = ['creatinine', 'serum creatinine', 'blood urea', 'random blood sugar', 'haemoglobin', 'hemoglobin', 'sodium', 'potassium']
        sorted_metrics = []
        for p in priority:
            for m in records_by_type:
                if m.lower() == p and m not in sorted_metrics:
                    sorted_metrics.append(m)
        for m in records_by_type:
            if m not in sorted_metrics:
                sorted_metrics.append(m)

        items = []
        for metric in sorted_metrics[:5]:
            latest_record = max(records_by_type[metric], key=lambda r: datetime.fromisoformat(r.timestamp))
            value = self._parse_value(latest_record.value)
            unit = latest_record.unit or self._get_default_unit(metric)
            norm_key = metric.lower()
            icon = "✓" if norm_key not in NORMAL_RANGES else ("✓" if NORMAL_RANGES[norm_key][0] <= value <= NORMAL_RANGES[norm_key][1] else "⚠️")
            val_str = f"{value:.0f}" if value >= 100 else f"{value:.1f}" if value >= 10 else f"{value:.2f}"
            items.append(f"{icon} {metric}: {val_str} {unit}")

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
        return {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
            'responsive': True,
            'scrollZoom': True,
            'doubleClick': 'reset',
            'toImageButtonOptions': {'format': 'png', 'filename': 'health_records', 'height': 800, 'width': 1200, 'scale': 2},
        }

    def _inject_mobile_css(self, html_content: str) -> str:
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
            /* Legend touch targets */
            .legend .traces { cursor: pointer; }
            /* Tablet */
            @media (max-width: 768px) { 
                body { padding: 4px; } 
                #health-graph { border-radius: 8px; } 
                .modebar { display: none !important; } 
            }
            /* Mobile */
            @media (max-width: 480px) { 
                body { padding: 2px; }
                /* Make legend items more compact on small screens */
                .legend .legendtext { font-size: 10px !important; }
            }
        </style>
        """
        return html_content.replace('<body>', f'<body>{mobile_css}')