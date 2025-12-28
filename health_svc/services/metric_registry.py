"""
Metric registry and parsing utilities for health records.

This module provides:
- MetricConfig dataclass for metric configuration
- YAML-based configuration loading
- Metric name normalization and lookup
- Value and timestamp parsing utilities
- Trend calculation and value formatting

This module is shared by GraphService and DataPreparationService
to avoid circular imports.
"""

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

import yaml

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
    """Load and parse the YAML configuration file (internal helper)."""
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


@lru_cache(maxsize=1)
def _load_full_config() -> Dict[str, Any]:
    """
    Load and cache the full YAML configuration.
    
    This function is cached to ensure the YAML file is loaded exactly once
    during the lifetime of the application.
    """
    return _load_yaml_config()


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


def _load_metric_configs(config: Dict[str, Any]) -> Tuple[MetricConfig, ...]:
    """Load all metric configurations from the provided config dict."""
    metrics_raw = config.get('metrics', [])
    return tuple(_parse_metric_config(m) for m in metrics_raw)


def _load_default_metric_config(config: Dict[str, Any]) -> MetricConfig:
    """Load the default metric configuration from the provided config dict."""
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


def _load_range_band_colors(config: Dict[str, Any]) -> Dict[str, str]:
    """Load reference band colors from the provided config dict."""
    return config.get('range_band_colors', {})


def _load_default_visible_metrics(config: Dict[str, Any]) -> Tuple[str, ...]:
    """Load default visible metrics from the provided config dict."""
    return tuple(config.get('default_visible_metrics', []))


# =============================================================================
# LOAD CONFIGURATION AT MODULE INIT
# =============================================================================

# Load YAML config exactly once at module initialization
_FULL_CONFIG: Dict[str, Any] = _load_full_config()

# Derive all configuration from the single loaded config
_METRIC_CONFIGS: Tuple[MetricConfig, ...] = _load_metric_configs(_FULL_CONFIG)
DEFAULT_METRIC_CONFIG: MetricConfig = _load_default_metric_config(_FULL_CONFIG)
RANGE_BAND_COLORS: Dict[str, str] = _load_range_band_colors(_FULL_CONFIG)
DEFAULT_VISIBLE_METRICS: Tuple[str, ...] = _load_default_visible_metrics(_FULL_CONFIG)


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
# TIMESTAMP PARSING
# =============================================================================

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

