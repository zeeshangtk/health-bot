"""
Plotly figure builder for health record visualization.

Responsibilities:
- Creating traces (standard metrics and blood pressure)
- Applying layout configuration
- Adding summary panel
- Adding annotations

This module encapsulates all Plotly-specific figure construction logic,
allowing GraphService to focus on orchestration.
"""

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

import plotly.graph_objects as go

from services.metric_registry import (
    MetricConfig,
    get_metric_config,
    format_metric_value,
    RANGE_BAND_COLORS,
)
from services.data_preparation_service import (
    PreparedMetricData,
    PreparedBloodPressureData,
    MetricSummary,
)

logger = logging.getLogger(__name__)


class PlotlyBuilder:
    """
    Builder for constructing Plotly figures for health record visualization.
    
    Encapsulates all Plotly-specific visualization logic:
    - Trace creation for metrics and blood pressure
    - Layout configuration with dual Y-axis support
    - Summary panel with latest readings
    - Help annotations
    
    Usage:
        builder = PlotlyBuilder()
        fig = builder.create_figure()
        builder.add_blood_pressure_trace(fig, bp_data)
        builder.add_metric_trace(fig, metric_data, is_visible=True)
        builder.apply_layout(fig, patient_name)
        builder.add_summary_panel(fig, summaries, latest_date)
    """

    def create_figure(self) -> go.Figure:
        """Create a new empty Plotly figure."""
        return go.Figure()

    def add_blood_pressure_trace(
        self, fig: go.Figure, bp_data: PreparedBloodPressureData
    ) -> None:
        """
        Add specialized blood pressure high-low chart.
        
        Uses pre-aligned data from DataPreparationService where systolic and
        diastolic values are guaranteed to be paired by timestamp.
        """
        dates = bp_data.timestamps
        sys_vals = bp_data.systolic_values
        dia_vals = bp_data.diastolic_values

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

    def create_metric_trace(
        self, metric_data: PreparedMetricData, is_visible: bool
    ) -> go.Scatter:
        """
        Create a Plotly trace with spline curves, value labels, and abnormal highlighting.
        
        Abnormal values are shown with:
        - Different marker symbol (diamond vs circle)
        - Contrasting fill color (warning red)
        - Enhanced size and opacity for accessibility
        This is clearer than border-only highlighting.
        
        UX Note: Legend shows metric name only for reduced cognitive load.
        Units and trends are shown in tooltips and summary panel instead.
        """
        config = metric_data.config
        values = metric_data.values
        is_abnormal = metric_data.is_abnormal
        unit = metric_data.unit
        
        # UX: Keep legend labels minimal - metric name only
        # Secondary info (units, trends) moved to tooltips and summary panel
        name = metric_data.metric_name.title()

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
            f"<b>{metric_data.metric_name.title()}</b><br>"
            f"{desc_line}"
            f"{range_line}"
            "%{x|%b %d, %Y}<br>"
            f"<b>Value: %{{y:.2f}} {unit}</b>"
            "<extra></extra>"
        )

        return go.Scatter(
            x=metric_data.timestamps,
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

    def add_reference_band(
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

    def apply_layout(self, fig: go.Figure, patient_name: str) -> None:
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

        # Add help annotation
        self.add_help_annotation(fig)

    def add_help_annotation(self, fig: go.Figure) -> None:
        """
        Add compact help annotation positioned below the legend.
        
        Provides guidance on interaction without cluttering the visualization.
        """
        fig.add_annotation(
            text="<i>Tap legend to show/hide  •  ◆ outside range  •  Right axis = micro values</i>",
            xref="paper", yref="paper",
            x=0.5, y=-0.18,  # UX: Moved closer to legend
            showarrow=False,
            font=dict(size=9, color='#BDBDBD'),  # UX: More muted
            xanchor='center'
        )

    def add_summary_panel(
        self, fig: go.Figure, summaries: List[MetricSummary], latest_date: datetime
    ) -> None:
        """
        Add summary panel with latest readings and trend indicators.
        
        Uses pre-prepared MetricSummary objects from DataPreparationService.
        
        UX Improvements:
        - Softer visual styling to not compete with main title
        - Semantic trend colors (green=improving, red=concerning, gray=stable)
        - Improved information hierarchy inside the panel
        """
        if not summaries:
            return

        items: List[str] = []
        for summary in summaries:
            # UX: Status indicator based on range check (subtle styling)
            if summary.is_abnormal:
                status_style = "color:#D32F2F"  # Red for abnormal
                status_marker = "●"
            else:
                status_style = "color:#4CAF50"  # Green for normal
                status_marker = "●"

            # UX: Semantic trend arrows with color coding
            # Green for improvement, red for concerning, gray for stable
            trend_html = ""
            if summary.trend == "↑":
                # For most metrics, rising is concerning; for some (like hemoglobin), it may be good
                # Simplified: use neutral color since context varies
                trend_html = "<span style='color:#757575;font-size:10px'> ↑</span>"
            elif summary.trend == "↓":
                trend_html = "<span style='color:#757575;font-size:10px'> ↓</span>"
            elif summary.trend == "→":
                trend_html = "<span style='color:#BDBDBD;font-size:10px'> →</span>"

            # UX: Compact item format with muted unit
            items.append(
                f"<span style='{status_style};font-size:8px'>{status_marker}</span> "
                f"{summary.metric_name.title()}: <b>{summary.formatted_value}</b>"
                f"<span style='color:#9E9E9E'> {summary.unit}</span>{trend_html}"
            )

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

    def apply_empty_layout(self, fig: go.Figure, patient_name: str) -> None:
        """Apply layout for empty graph (no records)."""
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

    def get_mobile_config(self) -> Dict[str, Any]:
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

    def inject_mobile_css(self, html_content: str) -> str:
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

