"""
Central metric registry - single source of truth for health metric definitions.

This module provides:
- YAML-based configuration loading and validation
- MetricDefinition dataclass for metric configuration
- Read-only access to metric definitions
- Metric lookup with canonical names (no fuzzy matching)
- Normal range checking

All metric-related logic in the application MUST derive from this registry.
YAML access is encapsulated here - no other module should read metrics.yaml directly.

Usage:
    from core.metric_registry import get_metric, list_metrics, is_abnormal, get_normal_range
    
    # Get a single metric definition
    metric = get_metric("creatinine")
    
    # List all metrics
    all_metrics = list_metrics()
    
    # Check if a value is abnormal
    abnormal = is_abnormal("creatinine", 1.5)
    
    # Get normal range
    range_tuple = get_normal_range("creatinine")  # (0.6, 1.2) or None
"""

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# METRIC DEFINITION DATACLASS
# =============================================================================

@dataclass(frozen=True)
class MetricDefinition:
    """
    Immutable definition for a health metric.
    
    Attributes:
        canonical_name: Primary identifier for the metric
        display_name: Human-readable name (defaults to title-cased canonical_name)
        color: Hex color code for visualization
        range: Normal reference range as (low, high) tuple, or None if unknown
        unit: Measurement unit (e.g., "mg/dL", "mmHg")
        axis: Y-axis assignment for graphing (y1=primary left, y2=secondary right)
        category: Grouping category (kidney, sugar, electrolyte, blood, liver, lipid, other)
        description: Educational tooltip text
        aliases: Alternative names that resolve to this metric
    """
    canonical_name: str
    display_name: str
    color: str
    range: Optional[Tuple[float, float]]
    unit: str
    axis: str
    category: str
    description: str
    aliases: Tuple[str, ...]

    def is_abnormal(self, value: float) -> bool:
        """
        Check if a value is outside the normal range.
        
        Args:
            value: The value to check
        
        Returns:
            True if abnormal (outside range), False if normal or no range defined
        """
        if self.range is None:
            return False
        low, high = self.range
        return not (low <= value <= high)


# Legacy alias for backward compatibility
MetricConfig = MetricDefinition


# =============================================================================
# YAML CONFIGURATION LOADING & VALIDATION
# =============================================================================

def _get_config_path() -> Path:
    """Get the path to the metrics configuration file."""
    return Path(__file__).parent / 'metrics.yaml'


def _load_yaml_config() -> Dict[str, Any]:
    """
    Load and parse the YAML configuration file.
    
    Raises:
        FileNotFoundError: If metrics.yaml is not found
        yaml.YAMLError: If YAML parsing fails
    """
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


def _validate_metric_entry(raw: Dict[str, Any], index: int) -> None:
    """
    Validate a single metric entry from YAML.
    
    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = ['canonical_name', 'color']
    for field in required_fields:
        if field not in raw:
            raise ValueError(f"Metric at index {index} is missing required field: '{field}'")
    
    # Validate color format (hex color)
    color = raw.get('color', '')
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError(f"Metric '{raw.get('canonical_name', 'unknown')}' has invalid color format: '{color}'")
    
    # Validate range if provided
    range_val = raw.get('range')
    if range_val is not None:
        if not isinstance(range_val, (list, tuple)) or len(range_val) != 2:
            raise ValueError(f"Metric '{raw['canonical_name']}' has invalid range: must be [low, high]")
        try:
            float(range_val[0])
            float(range_val[1])
        except (TypeError, ValueError):
            raise ValueError(f"Metric '{raw['canonical_name']}' has non-numeric range values")


def _parse_metric_entry(raw: Dict[str, Any]) -> MetricDefinition:
    """Parse a single metric entry from YAML into a MetricDefinition."""
    range_val = raw.get('range')
    parsed_range: Optional[Tuple[float, float]] = None
    if range_val is not None and len(range_val) == 2:
        parsed_range = (float(range_val[0]), float(range_val[1]))
    
    aliases = raw.get('aliases', [])
    if aliases is None:
        aliases = []
    
    canonical_name = raw['canonical_name']
    display_name = raw.get('display_name', canonical_name.title())
    
    return MetricDefinition(
        canonical_name=canonical_name,
        display_name=display_name,
        color=raw['color'],
        range=parsed_range,
        unit=raw.get('unit', ''),
        axis=raw.get('axis', 'y1'),
        category=raw.get('category', 'other'),
        description=raw.get('description', ''),
        aliases=tuple(aliases),
    )


@lru_cache(maxsize=1)
def _load_registry() -> Tuple[Tuple[MetricDefinition, ...], MetricDefinition, Dict[str, str], Tuple[str, ...]]:
    """
    Load and cache the complete metric registry from YAML.
    
    Returns a tuple of:
    - All metric definitions
    - Default metric definition
    - Range band colors by category
    - Default visible metrics
    
    This function is cached to ensure the YAML file is loaded exactly once
    during the lifetime of the application.
    """
    config = _load_yaml_config()
    
    # Validate and parse metric definitions
    metrics_raw = config.get('metrics', [])
    metric_definitions: List[MetricDefinition] = []
    
    for i, raw in enumerate(metrics_raw):
        _validate_metric_entry(raw, i)
        metric_definitions.append(_parse_metric_entry(raw))
    
    # Parse default metric
    default_raw = config.get('default_metric', {})
    default_metric = MetricDefinition(
        canonical_name='unknown',
        display_name='Unknown',
        color=default_raw.get('color', '#546E7A'),
        range=None,
        unit=default_raw.get('unit', ''),
        axis=default_raw.get('axis', 'y1'),
        category=default_raw.get('category', 'other'),
        description=default_raw.get('description', ''),
        aliases=(),
    )
    
    # Load range band colors
    range_band_colors = config.get('range_band_colors', {})
    
    # Load default visible metrics
    default_visible = tuple(config.get('default_visible_metrics', []))
    
    return (
        tuple(metric_definitions),
        default_metric,
        range_band_colors,
        default_visible,
    )


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


@lru_cache(maxsize=1)
def _build_metric_lookup() -> Dict[str, MetricDefinition]:
    """
    Build a normalized lookup map from all canonical names and aliases.
    Called once and cached.
    """
    metric_definitions, _, _, _ = _load_registry()
    
    lookup: Dict[str, MetricDefinition] = {}
    for metric in metric_definitions:
        # Register canonical name
        canonical_normalized = _normalize_metric_name(metric.canonical_name)
        if canonical_normalized in lookup:
            logger.warning(
                "Duplicate metric key detected",
                extra={'key': canonical_normalized, 'existing': lookup[canonical_normalized].canonical_name}
            )
        lookup[canonical_normalized] = metric
        
        # Register all aliases
        for alias in metric.aliases:
            alias_normalized = _normalize_metric_name(alias)
            if alias_normalized and alias_normalized not in lookup:
                lookup[alias_normalized] = metric
            elif alias_normalized in lookup and lookup[alias_normalized] != metric:
                logger.warning(
                    "Alias collision detected",
                    extra={'alias': alias_normalized, 'existing': lookup[alias_normalized].canonical_name}
                )
    return lookup


# =============================================================================
# MODULE-LEVEL CONSTANTS (Derived from YAML)
# =============================================================================

def _get_default_metric() -> MetricDefinition:
    """Get the default metric definition."""
    _, default_metric, _, _ = _load_registry()
    return default_metric


def _get_range_band_colors() -> Dict[str, str]:
    """Get range band colors by category."""
    _, _, range_band_colors, _ = _load_registry()
    return range_band_colors


def _get_default_visible_metrics() -> Tuple[str, ...]:
    """Get default visible metric canonical names."""
    _, _, _, default_visible = _load_registry()
    return default_visible


# Legacy exports for backward compatibility
DEFAULT_METRIC_CONFIG = property(lambda self: _get_default_metric())


# Load these at module level for backward compatibility
# They're derived from the cached registry load
def _init_module_constants():
    """Initialize module-level constants from registry."""
    pass


# Trigger registry load at import time
_load_registry()

# Expose constants
RANGE_BAND_COLORS: Dict[str, str] = _get_range_band_colors()
DEFAULT_VISIBLE_METRICS: Tuple[str, ...] = _get_default_visible_metrics()
DEFAULT_METRIC_CONFIG: MetricDefinition = _get_default_metric()


# =============================================================================
# PUBLIC API - METRIC ACCESS
# =============================================================================

def get_metric(metric_name: str) -> MetricDefinition:
    """
    Get metric definition by name.
    
    Uses exact normalized lookup only - no fuzzy/substring matching.
    Metric names are canonical; unknown metrics raise an explicit error.
    
    Args:
        metric_name: The metric name to look up (case-insensitive)
    
    Returns:
        MetricDefinition for the requested metric
    
    Raises:
        KeyError: If the metric is not found in the registry
    """
    normalized = _normalize_metric_name(metric_name)
    lookup = _build_metric_lookup()
    
    if normalized not in lookup:
        raise KeyError(f"Unknown metric: '{metric_name}' (normalized: '{normalized}')")
    
    return lookup[normalized]


def get_metric_config(metric_name: str) -> MetricDefinition:
    """
    Get metric definition by name with fallback to default.
    
    This is a backward-compatible version that returns DEFAULT_METRIC_CONFIG
    for unknown metrics instead of raising an error.
    
    Args:
        metric_name: The metric name to look up (case-insensitive)
    
    Returns:
        MetricDefinition for the requested metric, or DEFAULT_METRIC_CONFIG if unknown
    """
    normalized = _normalize_metric_name(metric_name)
    lookup = _build_metric_lookup()
    
    config = lookup.get(normalized)
    if config is None:
        logger.debug("Unknown metric, using default config", extra={'metric': metric_name, 'normalized': normalized})
        return DEFAULT_METRIC_CONFIG
    return config


def list_metrics() -> Dict[str, MetricDefinition]:
    """
    List all metric definitions.
    
    Returns:
        Dictionary mapping canonical metric names to their definitions
    """
    metric_definitions, _, _, _ = _load_registry()
    return {m.canonical_name: m for m in metric_definitions}


def is_abnormal(metric_name: str, value: float) -> bool:
    """
    Check if a value is outside the normal range for a metric.
    
    Args:
        metric_name: The metric to check
        value: The value to evaluate
    
    Returns:
        True if the value is abnormal (outside normal range),
        False if normal or if no range is defined
    
    Raises:
        KeyError: If the metric is not found in the registry
    """
    metric = get_metric(metric_name)
    if metric.range is None:
        return False
    low, high = metric.range
    return not (low <= value <= high)


def get_normal_range(metric_name: str) -> Optional[Tuple[float, float]]:
    """
    Get the normal reference range for a metric.
    
    Args:
        metric_name: The metric to look up
    
    Returns:
        Tuple of (low, high) if range is defined, None otherwise
    
    Raises:
        KeyError: If the metric is not found in the registry
    """
    return get_metric(metric_name).range


# =============================================================================
# UTILITY FUNCTIONS
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


def parse_timestamp(ts: str, record_id: Any = None) -> Optional[datetime]:
    """
    Safely parse an ISO timestamp string to datetime.
    
    Args:
        ts: ISO format timestamp string (e.g., "2025-01-15T10:30:00")
        record_id: Optional identifier for logging context
    
    Returns:
        Parsed datetime object, or None if parsing fails or input is missing.
    
    Logs a warning with structured metadata when parsing fails.
    """
    if ts is None:
        return None
    
    if not isinstance(ts, str):
        logger.warning(
            "Timestamp is not a string",
            extra={'record_id': record_id, 'type': type(ts).__name__}
        )
        return None
    
    ts_stripped = ts.strip()
    if not ts_stripped:
        return None
    
    try:
        return datetime.fromisoformat(ts_stripped)
    except ValueError as e:
        logger.warning(
            "Invalid timestamp format",
            extra={'record_id': record_id, 'timestamp': ts, 'error': str(e)}
        )
        return None


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


def format_metric_value(value: float) -> str:
    """Format a metric value for display with appropriate precision."""
    if value >= 100:
        return f"{value:.0f}"
    elif value >= 10:
        return f"{value:.1f}"
    else:
        return f"{value:.2f}"

