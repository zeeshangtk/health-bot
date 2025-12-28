"""
Service layer for generating health record visualization graphs.

Features:
- Unified metric registry with canonical names and aliases (loaded from YAML)
- Dual Y-axis support for metrics with different scales
- Blood pressure high-low chart visualization
- Semantic color coding by category
- Reference range bands (informational only)
- Abnormal value highlighting (filled markers + symbols)
- Touch-friendly markers and horizontal legend
- Educational metric descriptions in tooltips
- Summary panel with latest readings
- Date range filters and slider
- Spline curves for smooth visualization

Refactored for:
- Canonical metric + aliases model (no duplication)
- YAML-based configuration for easy maintenance
- Explicit normalized lookup (no fuzzy matching)
- Safe value parsing (None for unparseable)
- Improved abnormal visualization
- Datetime-based comparisons
- LRU cached lookups
"""

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

import yaml
import plotly.graph_objects as go
import plotly.io as pio

from api.schemas import HealthRecordResponse

logger = logging.getLogger(__name__)


# =============================================================================
# METRIC CONFIGURATION DATACLASS
# =============================================================================
@dataclass(frozen=True)
class MetricConfig:
    """Immutable configuration for a health metric."""
    canonical_name: str
    color: str
    range: Optional[Tuple[float, float]]
    unit: str
    axis: str
    category: str
    description: str
    aliases: Tuple[str, ...]  # Additional names that map to this metric

    def is_abnormal(self, value: float) -> bool:
        """Check if a value is outside the normal range."""
        if self.range is None:
            return False
        low, high = self.range
        return not (low <= value <= high)


# =============================================================================
# YAML CONFIGURATION LOADING
# =============================================================================

def _get_config_path() -> Path:
    """Get the path to the metrics configuration file."""
    # Config is located relative to this module's package
    return Path(__file__).parent.parent / 'config' / 'metrics.yaml'


def _load_yaml_config() -> Dict[str, Any]:
    """Load and parse the YAML configuration file."""
    config_path = _get_config_path()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("Metrics config file not found", extra={'path': str(config_path)})
        raise
    except yaml.YAMLError as e:
        logger.error("Failed to parse metrics config", extra={'path': str(config_path), 'error': str(e)})
        raise


def _parse_metric_config(raw: Dict[str, Any]) -> MetricConfig:
    """Parse a single metric entry from YAML into a MetricConfig."""
    range_val = raw.get('range')
    parsed_range: Optional[Tuple[float, float]] = None
    if range_val is not None and len(range_val) == 2:
        parsed_range = (float(range_val[0]), float(range_val[1]))
    
    aliases = raw.get('aliases', [])
    if aliases is None:
        aliases = []
    
    return MetricConfig(
        canonical_name=raw['canonical_name'],
        color=raw['color'],
        range=parsed_range,
        unit=raw.get('unit', ''),
        axis=raw.get('axis', 'y1'),
        category=raw.get('category', 'other'),
        description=raw.get('description', ''),
        aliases=tuple(aliases),
    )


def _load_metric_configs() -> Tuple[MetricConfig, ...]:
    """Load all metric configurations from YAML."""
    config = _load_yaml_config()
    metrics_raw = config.get('metrics', [])
    return tuple(_parse_metric_config(m) for m in metrics_raw)


def _load_default_metric_config() -> MetricConfig:
    """Load the default metric configuration from YAML."""
    config = _load_yaml_config()
    default_raw = config.get('default_metric', {})
    return MetricConfig(
        canonical_name='unknown',
        color=default_raw.get('color', '#546E7A'),
        range=None,
        unit=default_raw.get('unit', ''),
        axis=default_raw.get('axis', 'y1'),
        category=default_raw.get('category', 'other'),
        description=default_raw.get('description', ''),
        aliases=(),
    )


def _load_range_band_colors() -> Dict[str, str]:
    """Load reference band colors from YAML."""
    config = _load_yaml_config()
    return config.get('range_band_colors', {})


def _load_default_visible_metrics() -> Tuple[str, ...]:
    """Load default visible metrics from YAML."""
    config = _load_yaml_config()
    return tuple(config.get('default_visible_metrics', []))


# =============================================================================
# LOAD CONFIGURATION AT MODULE INIT
# =============================================================================

# Load once at module initialization
_METRIC_CONFIGS: Tuple[MetricConfig, ...] = _load_metric_configs()
DEFAULT_METRIC_CONFIG: MetricConfig = _load_default_metric_config()
RANGE_BAND_COLORS: Dict[str, str] = _load_range_band_colors()
DEFAULT_VISIBLE_METRICS: Tuple[str, ...] = _load_default_visible_metrics()


# =============================================================================
# METRIC NORMALIZATION & LOOKUP
# =============================================================================

def _normalize_metric_name(name: str) -> str:
    """
    Normalize a metric name for consistent lookup.
    
    Rules:
    - Convert to lowercase
    - Strip leading/trailing whitespace
    - Collapse multiple spaces to single space
    - Remove non-alphanumeric chars except spaces
    """
    if not name:
        return ''
    # Lowercase and strip
    normalized = name.lower().strip()
    # Remove non-alphanumeric except spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def _build_metric_lookup() -> Dict[str, MetricConfig]:
    """
    Build a normalized lookup map from all canonical names and aliases.
    Called once at module load.
    """
    lookup: Dict[str, MetricConfig] = {}
    for config in _METRIC_CONFIGS:
        # Register canonical name
        canonical_normalized = _normalize_metric_name(config.canonical_name)
        if canonical_normalized in lookup:
            logger.warning(
                "Duplicate metric key detected",
                extra={'key': canonical_normalized, 'existing': lookup[canonical_normalized].canonical_name}
            )
        lookup[canonical_normalized] = config
        
        # Register all aliases
        for alias in config.aliases:
            alias_normalized = _normalize_metric_name(alias)
            if alias_normalized and alias_normalized not in lookup:
                lookup[alias_normalized] = config
            elif alias_normalized in lookup and lookup[alias_normalized] != config:
                logger.warning(
                    "Alias collision detected",
                    extra={'alias': alias_normalized, 'existing': lookup[alias_normalized].canonical_name}
                )
    return lookup


# Build lookup once at module initialization
_METRIC_LOOKUP: Dict[str, MetricConfig] = _build_metric_lookup()


@lru_cache(maxsize=256)
def get_metric_config(metric_name: str) -> MetricConfig:
    """
    Get metric configuration by name (cached).
    
    Uses explicit normalized lookup only - no fuzzy/substring matching.
    Returns DEFAULT_METRIC_CONFIG for unknown metrics.
    """
    normalized = _normalize_metric_name(metric_name)
    config = _METRIC_LOOKUP.get(normalized)
    if config is None:
        logger.debug("Unknown metric, using default config", extra={'metric': metric_name, 'normalized': normalized})
        return DEFAULT_METRIC_CONFIG
    return config


# =============================================================================
# VALUE PARSING
# =============================================================================

def parse_metric_value(value_str: str, metric_name: str = '') -> Optional[float]:
    """
    Parse a metric value string to float.
    
    Returns None for:
    - Empty/whitespace strings
    - Composite values like "120/80" (blood pressure should be split beforehand)
    - Non-numeric strings
    
    Logs structured warnings for unparseable values.
    """
    if value_str is None:
        return None
    
    cleaned = str(value_str).strip()
    if not cleaned:
        return None
    
    # Reject composite values explicitly (e.g., blood pressure "120/80")
    if '/' in cleaned:
        logger.warning(
            "Composite value cannot be parsed as single metric",
            extra={'value': value_str, 'metric': metric_name, 'hint': 'Split into separate metrics'}
        )
        return None
    
    # Try direct float conversion first (most common case)
    try:
        return float(cleaned)
    except ValueError:
        pass
    
    # Extract numeric portion (handles cases like "5.6 mg/dl" or ">100")
    match = re.match(r'^[<>]?\s*(\d+\.?\d*)', cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    logger.warning(
        "Could not parse metric value",
        extra={'value': value_str, 'metric': metric_name}
    )
    return None


# =============================================================================
# TREND ANALYSIS
# =============================================================================

def calculate_trend(values: List[float], threshold_pct: float = 5.0, min_delta: float = 0.1) -> str:
    """
    Calculate trend indicator based on last two values.
    
    Returns:
    - "↑" if increasing by > threshold_pct or min_delta
    - "↓" if decreasing by > threshold_pct or min_delta
    - "→" if stable
    - "" if insufficient data
    
    Uses both percentage and absolute delta to avoid misleading trends
    for small values (e.g., creatinine changing 0.1 from 1.0).
    """
    if len(values) < 2:
        return ""
    
    prev, curr = values[-2], values[-1]
    
    # Absolute delta check (important for small-scale metrics)
    delta = curr - prev
    
    # Percentage calculation with safe division
    if abs(prev) < 1e-9:
        # Previous value effectively zero - use absolute delta only
        pct_change = 0.0
    else:
        pct_change = (delta / abs(prev)) * 100.0
    
    # Trend based on whichever threshold is exceeded
    if pct_change > threshold_pct or delta > min_delta:
        return "↑"
    elif pct_change < -threshold_pct or delta < -min_delta:
        return "↓"
    return "→"


# =============================================================================
# VALUE FORMATTING
# =============================================================================

def format_metric_value(value: float) -> str:
    """Format a metric value for display with appropriate precision."""
    if value >= 100:
        return f"{value:.0f}"
    elif value >= 10:
        return f"{value:.1f}"
    else:
        return f"{value:.2f}"


# =============================================================================
# GRAPH SERVICE
# =============================================================================

class GraphService:
    """
    Service for generating enhanced health record graphs with dual Y-axis support.
    
    This is the public orchestration layer that combines:
    - Metric registry lookups
    - Data preparation and validation
    - Plotly visualization construction
    """

    def generate_html_graph(self, records: List[HealthRecordResponse], patient_name: str) -> str:
        """Generate complete HTML with interactive Plotly graph."""
        if not records:
            return self._generate_empty_graph(patient_name)

        # Group by metric type (normalized)
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            records_by_type[record.record_type.lower()].append(record)

        visible_metrics = self._get_default_visible_metrics(list(records_by_type.keys()))
        fig = go.Figure()
        all_dates: List[datetime] = []

        # Handle Blood Pressure specially (systolic/diastolic as range chart)
        if 'systolic' in records_by_type and 'diastolic' in records_by_type:
            bp_dates = self._add_blood_pressure_trace(fig, records_by_type)
            all_dates.extend(bp_dates)
            del records_by_type['systolic']
            del records_by_type['diastolic']

        # Add standard traces
        for record_type, type_records in records_by_type.items():
            trace_data = self._prepare_trace_data(record_type, type_records)
            if not trace_data['values']:
                # Skip metrics with no valid values
                continue
            all_dates.extend(trace_data['timestamps'])
            is_visible = record_type in visible_metrics
            fig.add_trace(self._create_trace(record_type, trace_data, is_visible))

        # Date range for reference bands
        if all_dates:
            date_range = (min(all_dates), max(all_dates))
        else:
            now = datetime.now()
            date_range = (now, now)

        # Reference bands removed - they caused visual clutter with multiple metrics
        # If needed in future, consider showing only for the selected/visible metric

        # Apply layout and add summary
        self._apply_layout(fig, patient_name)
        self._add_summary_panel(fig, records_by_type, date_range[1])

        html_content = pio.to_html(
            fig,
            include_plotlyjs='cdn',
            config=self._get_mobile_config(),
            div_id="health-graph"
        )

        return self._inject_mobile_css(html_content)

    # =========================================================================
    # Private Methods
    # =========================================================================

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
        """Determine which metrics to show by default (max 3)."""
        visible = []
        
        # First pass: exact match on canonical names
        for priority in DEFAULT_VISIBLE_METRICS:
            if priority in available_metrics and priority not in visible:
                visible.append(priority)
                if len(visible) >= 3:
                    break
        
        # Second pass: check if available metrics are aliases of priority metrics
        if len(visible) < 3:
            for metric in available_metrics:
                config = get_metric_config(metric)
                if config.canonical_name in DEFAULT_VISIBLE_METRICS and metric not in visible:
                    visible.append(metric)
                    if len(visible) >= 3:
                        break
        
        # Fallback: fill with any available metrics
        if len(visible) < 2:
            for m in available_metrics:
                if m not in visible:
                    visible.append(m)
                    if len(visible) >= 2:
                        break
        
        return visible

    def _prepare_trace_data(
        self, record_type: str, type_records: List[HealthRecordResponse]
    ) -> Dict[str, Any]:
        """
        Prepare data for a trace with abnormal detection.
        
        Filters out records with unparseable values.
        """
        sorted_records = sorted(type_records, key=lambda x: x.timestamp)
        
        timestamps: List[datetime] = []
        values: List[float] = []
        
        for r in sorted_records:
            try:
                ts = datetime.fromisoformat(r.timestamp)
            except (ValueError, AttributeError) as e:
                logger.warning("Invalid timestamp", extra={'record_id': getattr(r, 'id', 'unknown'), 'error': str(e)})
                continue
            
            parsed = parse_metric_value(r.value, record_type)
            if parsed is None:
                # Skip records with unparseable values
                continue
            
            timestamps.append(ts)
            values.append(parsed)

        config = get_metric_config(record_type)
        
        # Determine unit from first record or fallback to config
        unit = ''
        if sorted_records and sorted_records[0].unit:
            unit = sorted_records[0].unit
        else:
            unit = config.unit
        
        # Compute abnormal flags for each value
        is_abnormal = [config.is_abnormal(v) for v in values]

        return {
            'timestamps': timestamps,
            'values': values,
            'unit': unit,
            'is_abnormal': is_abnormal,
            'config': config,
        }

    def _add_blood_pressure_trace(
        self, fig: go.Figure, records_by_type: Dict[str, List[HealthRecordResponse]]
    ) -> List[datetime]:
        """
        Add specialized blood pressure high-low chart.
        
        Returns list of parsed dates for date range calculation.
        """
        sys_records = sorted(records_by_type['systolic'], key=lambda x: x.timestamp)
        dia_records = sorted(records_by_type['diastolic'], key=lambda x: x.timestamp)

        dates: List[datetime] = []
        sys_vals: List[float] = []
        dia_vals: List[float] = []
        
        # Parse systolic values
        for r in sys_records:
            try:
                ts = datetime.fromisoformat(r.timestamp)
            except ValueError:
                continue
            val = parse_metric_value(r.value, 'systolic')
            if val is not None:
                dates.append(ts)
                sys_vals.append(val)
        
        # Parse diastolic values (assuming aligned with systolic by timestamp)
        for r in dia_records:
            val = parse_metric_value(r.value, 'diastolic')
            if val is not None:
                dia_vals.append(val)

        if not dates or not sys_vals or not dia_vals:
            return []
        
        # Ensure equal length (use minimum)
        min_len = min(len(dates), len(sys_vals), len(dia_vals))
        dates = dates[:min_len]
        sys_vals = sys_vals[:min_len]
        dia_vals = dia_vals[:min_len]

        # UX: Blood pressure traces have distinct visual styling
        # - Darker, bolder appearance vs other metrics
        # - Fill between traces emphasizes the range
        # - Dash pattern on diastolic for additional differentiation
        
        # Systolic trace (top of BP range)
        fig.add_trace(go.Scatter(
            x=dates, y=sys_vals,
            name="Systolic",  # UX: Minimal legend - no arrows
            mode='lines+markers',
            line=dict(color='#263238', width=2.5, shape='spline'),  # Darker, slightly thinner
            marker=dict(
                size=9,
                color='#263238',
                symbol='triangle-up',  # UX: Triangle hints at "upper" value
                line=dict(width=1.5, color='white')
            ),
            hovertemplate=(
                "<b>Systolic (Upper)</b><br>"
                "<span style='color:#666'>Normal: 90–120 mmHg</span><br>"
                "%{x|%b %d, %Y}<br>"
                "<b>Value: %{y} mmHg</b>"
                "<extra></extra>"
            ),
        ))

        # Diastolic trace with fill to systolic (bottom of BP range)
        fig.add_trace(go.Scatter(
            x=dates, y=dia_vals,
            name="Diastolic",  # UX: Minimal legend - no arrows
            mode='lines+markers',
            line=dict(color='#607D8B', width=2.5, shape='spline', dash='dot'),  # UX: Dotted line distinguishes from systolic
            marker=dict(
                size=9,
                color='#607D8B',
                symbol='triangle-down',  # UX: Triangle hints at "lower" value
                line=dict(width=1.5, color='white')
            ),
            fill='tonexty',
            fillcolor='rgba(38, 50, 56, 0.08)',  # UX: More subtle fill
            hovertemplate=(
                "<b>Diastolic (Lower)</b><br>"
                "<span style='color:#666'>Normal: 60–80 mmHg</span><br>"
                "%{x|%b %d, %Y}<br>"
                "<b>Value: %{y} mmHg</b>"
                "<extra></extra>"
            ),
        ))
        
        return dates

    def _create_trace(
        self, record_type: str, trace_data: Dict[str, Any], is_visible: bool
    ) -> go.Scatter:
        """
        Create a trace with spline curves, value labels, and abnormal highlighting.
        
        Abnormal values are shown with:
        - Different marker symbol (diamond vs circle)
        - Contrasting fill color (warning red)
        - Enhanced size and opacity for accessibility
        This is clearer than border-only highlighting.
        
        UX Note: Legend shows metric name only for reduced cognitive load.
        Units and trends are shown in tooltips and summary panel instead.
        """
        config: MetricConfig = trace_data['config']
        values = trace_data['values']
        is_abnormal = trace_data['is_abnormal']
        unit = trace_data['unit']
        
        # UX: Keep legend labels minimal - metric name only
        # Secondary info (units, trends) moved to tooltips and summary panel
        name = record_type.title()

        # UX: Enhanced abnormal marker visibility
        # - Larger size differential for quick scanning
        # - Higher opacity contrast for accessibility
        # - Distinct border color for additional differentiation
        marker_colors = [
            '#D32F2F' if abnormal else config.color  # Slightly deeper red for abnormal
            for abnormal in is_abnormal
        ]
        marker_symbols = [
            'diamond' if abnormal else 'circle'
            for abnormal in is_abnormal
        ]
        marker_sizes = [
            16 if abnormal else 11  # Increased size contrast (was 14 vs 12)
            for abnormal in is_abnormal
        ]
        # UX: Subtle border color hint for abnormal values
        marker_line_colors = [
            '#FFCDD2' if abnormal else 'white'  # Light red border for abnormal
            for abnormal in is_abnormal
        ]
        marker_line_widths = [
            2.5 if abnormal else 2
            for abnormal in is_abnormal
        ]

        # Value labels with smart formatting
        text_labels = [format_metric_value(v) for v in values]

        # UX: Enhanced tooltip with reference range information
        # Provides clinical context without cluttering the graph
        desc_line = f"<i>{config.description}</i><br>" if config.description else ""
        range_line = ""
        if config.range:
            low, high = config.range
            range_line = f"<span style='color:#666'>Normal: {low}–{high} {unit}</span><br>"
        
        hovertemplate = (
            f"<b>{record_type.title()}</b><br>"
            f"{desc_line}"
            f"{range_line}"
            "%{x|%b %d, %Y}<br>"
            f"<b>Value: %{{y:.2f}} {unit}</b>"
            "<extra></extra>"
        )

        return go.Scatter(
            x=trace_data['timestamps'],
            y=values,
            yaxis=config.axis,
            name=name,
            visible=True if is_visible else "legendonly",
            mode='lines+markers+text',
            line=dict(width=3, color=config.color, shape='spline'),  # Slightly thinner line
            marker=dict(
                size=marker_sizes,
                color=marker_colors,
                symbol=marker_symbols,
                line=dict(width=marker_line_widths, color=marker_line_colors),
                opacity=[0.95 if abnormal else 0.9 for abnormal in is_abnormal],  # UX: Subtle opacity boost for abnormal
            ),
            text=text_labels,
            textposition='top center',
            textfont=dict(size=10, color='#616161'),
            connectgaps=True,
            hovertemplate=hovertemplate,
        )

    def _add_reference_band(
        self, fig: go.Figure, record_type: str, date_range: Tuple[datetime, datetime]
    ) -> None:
        """Add subtle reference range band for a metric."""
        config = get_metric_config(record_type)
        if config.range is None:
            return

        low, high = config.range
        fill_color = RANGE_BAND_COLORS.get(config.category, RANGE_BAND_COLORS.get('other', 'rgba(117, 117, 117, 0.08)'))

        # Extend range slightly for visual padding
        x0 = date_range[0] - timedelta(days=7)
        x1 = date_range[1] + timedelta(days=7)

        fig.add_shape(
            type="rect",
            x0=x0, x1=x1,
            y0=low, y1=high,
            yref=config.axis,
            fillcolor=fill_color,
            line=dict(width=0),
            layer="below",
        )

    def _apply_layout(self, fig: go.Figure, patient_name: str) -> None:
        """
        Apply layout with dual Y-axis support.
        
        UX Improvements:
        - Tighter vertical spacing (reduced bottom margin)
        - Cleaner legend with minimal labels
        - Mobile-friendly date tick density via JavaScript injection
        """
        fig.update_layout(
            title=dict(
                text=f"<b>Health Trends</b><br><sup style='color:#757575'>{patient_name}</sup>",
                font=dict(size=18),  # UX: Slightly smaller title
                x=0.5, xanchor="center"
            ),
            xaxis=dict(
                # No title - dates are self-explanatory from axis labels
                type="date",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.06)',  # UX: Lighter grid
                tickformat='%b %d',  # Default format; mobile override via JS
                tickangle=-45,  # UX: Angled labels prevent overlap
                nticks=8,  # UX: Limit tick density for readability
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
                    font=dict(size=11),  # UX: Smaller range selector text
                ),
                rangeslider=dict(visible=True, thickness=0.04),  # UX: Thinner slider
            ),
            # Primary Y-axis (left) for larger values
            yaxis=dict(
                title=dict(text="Primary", font=dict(size=11, color='#9E9E9E')),  # UX: Muted axis title
                side="left",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.06)',
            ),
            # Secondary Y-axis (right) for small decimal values
            yaxis2=dict(
                title=dict(text="Micro", font=dict(size=11, color='#9E9E9E')),  # UX: Muted axis title
                side="right",
                overlaying="y",
                showgrid=False,
            ),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                x=0.5, xanchor="center",
                y=-0.12, yanchor="top",  # UX: Moved closer to plot
                font=dict(size=11, color='#424242'),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="rgba(0,0,0,0.08)",  # UX: Lighter border
                borderwidth=1,
                # UX: Responsive grid layout for legend items
                entrywidth=0.28,  # Slightly narrower for tighter layout
                entrywidthmode="fraction",
                itemwidth=30,  # Minimum allowed by Plotly is 30
                tracegroupgap=4,  # UX: Reduced vertical gap between rows
                itemsizing='constant',
            ),
            height=700,  # UX: Reduced overall height
            margin=dict(l=50, r=50, t=90, b=140),  # UX: Tighter margins
            template="plotly_white",
            paper_bgcolor='#FAFAFA',
            plot_bgcolor='#FFFFFF',
            dragmode='pan',
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                bordercolor='rgba(0,0,0,0.1)',
            ),
        )

        # UX: Compact help annotation positioned closer to legend
        fig.add_annotation(
            text="<i>Tap legend to show/hide  •  ◆ outside range  •  Right axis = micro values</i>",
            xref="paper", yref="paper",
            x=0.5, y=-0.18,  # UX: Moved closer to legend
            showarrow=False,
            font=dict(size=9, color='#BDBDBD'),  # UX: More muted
            xanchor='center'
        )

    def _add_summary_panel(
        self, fig: go.Figure, records_by_type: Dict[str, List[HealthRecordResponse]], latest_date: datetime
    ) -> None:
        """
        Add summary panel with latest readings and trend indicators.
        
        UX Improvements:
        - Softer visual styling to not compete with main title
        - Semantic trend colors (green=improving, red=concerning, gray=stable)
        - Improved information hierarchy inside the panel
        
        Uses datetime comparison (not string) for finding latest record.
        """
        # Priority order for summary display
        priority = ('creatinine', 'blood urea', 'random blood sugar',
                    'haemoglobin', 'sodium', 'potassium')
        
        # Sort metrics: priority first, then alphabetically
        sorted_metrics: List[str] = []
        for p in priority:
            for m in records_by_type:
                config = get_metric_config(m)
                if (m == p or config.canonical_name == p) and m not in sorted_metrics:
                    sorted_metrics.append(m)
                    break
        for m in sorted(records_by_type.keys()):
            if m not in sorted_metrics:
                sorted_metrics.append(m)

        items: List[str] = []
        for metric in sorted_metrics[:5]:
            type_records = records_by_type[metric]
            if not type_records:
                continue
            
            # Find latest record and compute trend
            sorted_records = sorted(type_records, key=lambda x: x.timestamp)
            values_for_trend: List[float] = []
            latest_record = None
            latest_ts: Optional[datetime] = None
            
            for r in sorted_records:
                try:
                    ts = datetime.fromisoformat(r.timestamp)
                except ValueError:
                    continue
                val = parse_metric_value(r.value, metric)
                if val is not None:
                    values_for_trend.append(val)
                    if latest_ts is None or ts > latest_ts:
                        latest_ts = ts
                        latest_record = r
            
            if latest_record is None:
                continue
            
            value = parse_metric_value(latest_record.value, metric)
            if value is None:
                continue
            
            config = get_metric_config(metric)
            unit = latest_record.unit or config.unit

            # UX: Status indicator based on range check (subtle styling)
            is_abnormal = config.is_abnormal(value)
            if is_abnormal:
                status_style = "color:#D32F2F"  # Red for abnormal
                status_marker = "●"
            else:
                status_style = "color:#4CAF50"  # Green for normal
                status_marker = "●"

            # UX: Semantic trend arrows with color coding
            # Green for improvement, red for concerning, gray for stable
            trend = calculate_trend(values_for_trend)
            trend_html = ""
            if trend == "↑":
                # For most metrics, rising is concerning; for some (like hemoglobin), it may be good
                # Simplified: use neutral color since context varies
                trend_html = "<span style='color:#757575;font-size:10px'> ↑</span>"
            elif trend == "↓":
                trend_html = "<span style='color:#757575;font-size:10px'> ↓</span>"
            elif trend == "→":
                trend_html = "<span style='color:#BDBDBD;font-size:10px'> →</span>"

            val_str = format_metric_value(value)
            # UX: Compact item format with muted unit
            items.append(
                f"<span style='{status_style};font-size:8px'>{status_marker}</span> "
                f"{metric.title()}: <b>{val_str}</b>"
                f"<span style='color:#9E9E9E'> {unit}</span>{trend_html}"
            )

        if not items:
            return

        # UX: Softer header styling - informational, not dominant
        header = f"<span style='color:#757575;font-size:10px'>LATEST • {latest_date.strftime('%b %d')}</span>"
        summary_text = header + "<br>" + "<br>".join(items)
        
        fig.add_annotation(
            text=summary_text,
            xref="paper", yref="paper",
            x=1.0, y=1.0,
            xanchor='right', yanchor='top',
            showarrow=False,
            font=dict(size=10, color='#424242'),  # UX: Smaller, muted text
            align='left',
            bgcolor='rgba(250,250,250,0.92)',  # UX: Softer background
            bordercolor='rgba(0,0,0,0.06)',  # UX: Very subtle border
            borderwidth=1,
            borderpad=6,  # UX: Tighter padding
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
        """
        Inject mobile-responsive CSS and JavaScript.
        
        UX Improvements:
        - Responsive date tick formatting (month-only on mobile)
        - Reduced legend text size on small screens
        - Smoother touch interactions
        """
        mobile_enhancements = """
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                padding: 8px;
                background: #FAFAFA;
                font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                -webkit-font-smoothing: antialiased;
            }
            #health-graph {
                width: 100% !important;
                max-width: 100%;
                border-radius: 10px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.06);
                background: white;
            }
            .js-plotly-plot { width: 100% !important; }
            .legend .traces { cursor: pointer; }
            
            /* UX: Tablet and below */
            @media (max-width: 768px) {
                body { padding: 4px; }
                #health-graph { border-radius: 8px; }
                .modebar { display: none !important; }
                /* UX: Compact legend on tablet */
                .legend .legendtext { font-size: 10px !important; }
            }
            
            /* UX: Mobile - aggressive space optimization */
            @media (max-width: 480px) {
                body { padding: 2px; }
                .legend .legendtext { font-size: 9px !important; }
                /* UX: Hide secondary annotations on very small screens */
                .annotation-text { font-size: 8px !important; }
            }
        </style>
        
        <script>
        // UX: Responsive X-axis date formatting
        // Mobile shows month-only labels to prevent overlap
        (function() {
            function updateTickFormat() {
                var graphDiv = document.getElementById('health-graph');
                if (!graphDiv || !graphDiv.layout) return;
                
                var isMobile = window.innerWidth < 600;
                var tickFormat = isMobile ? '%b' : '%b %d';  // Month-only on mobile
                var nticks = isMobile ? 5 : 8;  // Fewer ticks on mobile
                
                Plotly.relayout(graphDiv, {
                    'xaxis.tickformat': tickFormat,
                    'xaxis.nticks': nticks
                });
            }
            
            // Apply on load and resize
            window.addEventListener('load', function() {
                setTimeout(updateTickFormat, 100);
            });
            
            var resizeTimeout;
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(updateTickFormat, 150);
            });
        })();
        </script>
        """
        return html_content.replace('<body>', f'<body>{mobile_enhancements}')
