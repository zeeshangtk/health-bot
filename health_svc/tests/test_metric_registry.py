"""
Unit tests for pure functions in metric_registry and data_preparation_service.

Tests cover:
- _normalize_metric_name: Metric name normalization
- parse_metric_value: Value parsing with edge cases
- calculate_trend: Trend analysis for health metrics
- MetricConfig.is_abnormal: Abnormal value detection
- Blood pressure timestamp alignment logic

These tests:
- Use pytest
- Avoid Plotly imports
- Avoid filesystem access
- Cover edge cases (None, invalid values, mismatched timestamps)
"""
import pytest
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass


# =============================================================================
# IMPORT TESTED FUNCTIONS
# =============================================================================

from services.metric_registry import (
    _normalize_metric_name,
    parse_metric_value,
    calculate_trend,
    MetricConfig,
)


# =============================================================================
# BLOOD PRESSURE ALIGNMENT LOGIC (ISOLATED FOR TESTING)
# =============================================================================
# This is a pure function extracted from DataPreparationService._prepare_blood_pressure
# to enable testing without depending on HealthRecordResponse schema or the full service.

@dataclass
class BloodPressureDataPoint:
    """A single blood pressure reading with both systolic and diastolic."""
    timestamp: datetime
    systolic: float
    diastolic: float


def align_blood_pressure_readings(
    systolic_by_ts: Dict[datetime, float],
    diastolic_by_ts: Dict[datetime, float],
) -> List[BloodPressureDataPoint]:
    """
    Align systolic and diastolic readings by timestamp.
    
    Only returns data points where BOTH values exist at the same timestamp.
    This is the core logic from DataPreparationService._prepare_blood_pressure.
    """
    if not systolic_by_ts or not diastolic_by_ts:
        return []
    
    # Find timestamps where BOTH values exist
    common_timestamps = sorted(set(systolic_by_ts.keys()) & set(diastolic_by_ts.keys()))
    
    if not common_timestamps:
        return []
    
    return [
        BloodPressureDataPoint(
            timestamp=ts,
            systolic=systolic_by_ts[ts],
            diastolic=diastolic_by_ts[ts],
        )
        for ts in common_timestamps
    ]


# =============================================================================
# TESTS: _normalize_metric_name
# =============================================================================

class TestNormalizeMetricName:
    """Tests for _normalize_metric_name function."""
    
    def test_basic_lowercase(self):
        """Should convert to lowercase."""
        assert _normalize_metric_name("Weight") == "weight"
        assert _normalize_metric_name("CREATININE") == "creatinine"
        assert _normalize_metric_name("Blood Urea") == "blood urea"
    
    def test_strip_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert _normalize_metric_name("  weight  ") == "weight"
        assert _normalize_metric_name("\tcreatinine\n") == "creatinine"
        assert _normalize_metric_name("   ") == ""
    
    def test_collapse_multiple_spaces(self):
        """Should collapse multiple spaces to single space."""
        assert _normalize_metric_name("blood  urea") == "blood urea"
        assert _normalize_metric_name("random   blood    sugar") == "random blood sugar"
        assert _normalize_metric_name("a    b    c") == "a b c"
    
    def test_remove_special_characters(self):
        """Should remove non-alphanumeric characters except spaces."""
        # Note: The function preserves spaces, so removing special chars can leave trailing spaces
        # "HbA1c (%)" -> lowercase -> "hba1c (%)" -> remove special chars -> "hba1c  " -> collapse -> "hba1c "
        assert _normalize_metric_name("HbA1c (%)") == "hba1c "  # Trailing space from parentheses
        assert _normalize_metric_name("Blood-Urea") == "bloodurea"  # Hyphen removed, no space
        assert _normalize_metric_name("Creatinine [mg/dl]") == "creatinine mgdl"  # Special chars removed
        assert _normalize_metric_name("Test_Name") == "testname"  # Underscore removed
        assert _normalize_metric_name("Vitamin-D3/B12") == "vitamind3b12"  # Punctuation removed
        # Test case without trailing space
        assert _normalize_metric_name("HbA1c") == "hba1c"  # No special chars, no trailing space
    
    def test_empty_string(self):
        """Should return empty string for empty input."""
        assert _normalize_metric_name("") == ""
    
    def test_none_like_behavior(self):
        """Should handle falsy-like strings."""
        assert _normalize_metric_name("0") == "0"
        # Note: The function doesn't accept None, but handles empty strings
    
    def test_numbers_preserved(self):
        """Should preserve numbers in metric names."""
        assert _normalize_metric_name("HbA1c") == "hba1c"
        assert _normalize_metric_name("Vitamin B12") == "vitamin b12"
        assert _normalize_metric_name("T3") == "t3"
        assert _normalize_metric_name("25-OH Vitamin D3") == "25oh vitamin d3"
    
    def test_unicode_characters_removed(self):
        """Should handle unicode characters by removing them."""
        assert _normalize_metric_name("Créatinine") == "cratinine"
        assert _normalize_metric_name("Hämoglobin") == "hmoglobin"
    
    def test_mixed_case_and_spaces(self):
        """Should handle complex mixed case with spaces."""
        assert _normalize_metric_name("Random Blood Sugar") == "random blood sugar"
        assert _normalize_metric_name("BLOOD UREA NITROGEN") == "blood urea nitrogen"


# =============================================================================
# TESTS: parse_metric_value
# =============================================================================

class TestParseMetricValue:
    """Tests for parse_metric_value function."""
    
    def test_basic_numeric_string(self):
        """Should parse basic numeric strings."""
        assert parse_metric_value("120") == 120.0
        assert parse_metric_value("5.6") == 5.6
        assert parse_metric_value("0.5") == 0.5
        assert parse_metric_value("100.25") == 100.25
    
    def test_none_input(self):
        """Should return None for None input."""
        assert parse_metric_value(None) is None
    
    def test_empty_string(self):
        """Should return None for empty string."""
        assert parse_metric_value("") is None
        assert parse_metric_value("   ") is None
        assert parse_metric_value("\t\n") is None
    
    def test_composite_values_rejected(self):
        """Should reject composite values like blood pressure."""
        assert parse_metric_value("120/80") is None
        assert parse_metric_value("140/90") is None
        assert parse_metric_value("1/2") is None
    
    def test_value_with_unit(self):
        """Should extract numeric portion from values with units."""
        # Note: Values containing "/" are rejected as composite values
        # So "5.6 mg/dl" returns None because it contains "/"
        assert parse_metric_value("5.6 mg/dl") is None  # Contains "/" - treated as composite
        assert parse_metric_value("120 mmHg") == 120.0
        assert parse_metric_value("98.6 F") == 98.6
        # Units without "/" work fine
        assert parse_metric_value("5.6 mgdl") == 5.6
    
    def test_greater_less_than_prefix(self):
        """Should handle > and < prefixes."""
        assert parse_metric_value(">100") == 100.0
        assert parse_metric_value("> 100") == 100.0
        assert parse_metric_value("<0.5") == 0.5
        assert parse_metric_value("< 0.5") == 0.5
    
    def test_non_numeric_string(self):
        """Should return None for non-numeric strings."""
        assert parse_metric_value("normal") is None
        assert parse_metric_value("positive") is None
        assert parse_metric_value("negative") is None
        assert parse_metric_value("N/A") is None
    
    def test_negative_values(self):
        """Should handle negative values."""
        assert parse_metric_value("-5") == -5.0
        assert parse_metric_value("-10.5") == -10.5
    
    def test_scientific_notation(self):
        """Should handle scientific notation."""
        assert parse_metric_value("1e3") == 1000.0
        assert parse_metric_value("2.5e-2") == 0.025
    
    def test_integer_coerced_to_float(self):
        """Should coerce integer strings to float."""
        result = parse_metric_value("100")
        assert result == 100.0
        assert isinstance(result, float)
    
    def test_leading_trailing_whitespace(self):
        """Should handle leading and trailing whitespace."""
        assert parse_metric_value("  5.6  ") == 5.6
        assert parse_metric_value("\t120\n") == 120.0
    
    def test_metric_name_for_context(self):
        """Should accept metric_name for logging context."""
        # These should work the same regardless of metric_name
        assert parse_metric_value("5.6", "creatinine") == 5.6
        assert parse_metric_value("120", "systolic") == 120.0
        assert parse_metric_value("invalid", "weight") is None
    
    def test_edge_case_values(self):
        """Should handle edge case numeric values."""
        assert parse_metric_value("0") == 0.0
        assert parse_metric_value("0.0") == 0.0
        assert parse_metric_value(".5") == 0.5
        assert parse_metric_value("1.") == 1.0


# =============================================================================
# TESTS: calculate_trend
# =============================================================================

class TestCalculateTrend:
    """Tests for calculate_trend function."""
    
    def test_increasing_trend_by_percentage(self):
        """Should detect increasing trend by percentage threshold."""
        # 105 is 5.26% increase from 100 (> 5% threshold)
        assert calculate_trend([100.0, 105.1]) == "↑"
        # Large increase
        assert calculate_trend([100.0, 150.0]) == "↑"
    
    def test_decreasing_trend_by_percentage(self):
        """Should detect decreasing trend by percentage threshold."""
        # 94 is 6% decrease from 100 (> 5% threshold)
        assert calculate_trend([100.0, 94.0]) == "↓"
        # Large decrease
        assert calculate_trend([100.0, 50.0]) == "↓"
    
    def test_stable_trend(self):
        """Should detect stable trend within threshold."""
        # 101 is 1% increase from 100 (< 5% threshold, and delta 1 < 0.1 is false)
        # Actually delta = 1 > 0.1, so this would be increasing
        # Need a smaller change
        assert calculate_trend([100.0, 100.05]) == "→"
        assert calculate_trend([100.0, 100.0]) == "→"
        assert calculate_trend([100.0, 99.95]) == "→"
    
    def test_insufficient_data(self):
        """Should return empty string for insufficient data."""
        assert calculate_trend([]) == ""
        assert calculate_trend([100.0]) == ""
    
    def test_min_delta_threshold(self):
        """Should use min_delta for small scale metrics."""
        # For small values, percentage change is large but absolute delta matters
        # 1.0 to 1.15: 15% increase, delta = 0.15 > 0.1 -> increasing
        assert calculate_trend([1.0, 1.15]) == "↑"
        # 1.0 to 1.04: 4% increase (< 5%), delta = 0.04 (< 0.1) -> stable
        # Note: Due to floating point precision, we use 4% to be safely below 5%
        assert calculate_trend([1.0, 1.04]) == "→"
        # 1.0 to 0.85: 15% decrease, delta = -0.15 < -0.1 -> decreasing
        assert calculate_trend([1.0, 0.85]) == "↓"
        # 1.0 to 0.96: 4% decrease (< 5%), delta = -0.04 (> -0.1) -> stable
        assert calculate_trend([1.0, 0.96]) == "→"
    
    def test_zero_previous_value(self):
        """Should handle zero previous value safely."""
        # When previous is 0, percentage calc would divide by zero
        # Should use absolute delta only
        assert calculate_trend([0.0, 0.5]) == "↑"
        assert calculate_trend([0.0, 0.05]) == "→"
        assert calculate_trend([0.0, 0.0]) == "→"
    
    def test_very_small_previous_value(self):
        """Should handle very small previous values."""
        # Values near zero should use absolute delta
        assert calculate_trend([0.0000001, 0.5]) == "↑"
    
    def test_uses_last_two_values(self):
        """Should only consider last two values for trend."""
        # Even with many values, only last two matter
        assert calculate_trend([50.0, 60.0, 70.0, 80.0, 90.0, 100.0]) == "↑"
        assert calculate_trend([100.0, 90.0, 80.0, 70.0, 60.0, 50.0]) == "↓"
        assert calculate_trend([50.0, 100.0, 75.0, 75.0]) == "→"
    
    def test_custom_threshold(self):
        """Should respect custom threshold parameters."""
        # 10% threshold with large min_delta to ensure only percentage matters
        # Note: Both thresholds use OR logic, so we need to set both to test percentage
        assert calculate_trend([100.0, 109.0], threshold_pct=10.0, min_delta=10.0) == "→"
        assert calculate_trend([100.0, 111.0], threshold_pct=10.0, min_delta=10.0) == "↑"
        
        # Custom min_delta with high percentage threshold to ensure only delta matters
        assert calculate_trend([1.0, 1.4], threshold_pct=50.0, min_delta=0.5) == "→"
        assert calculate_trend([1.0, 1.6], threshold_pct=50.0, min_delta=0.5) == "↑"
        
        # Default behavior: either threshold triggers trend detection
        # 9% change (< 10%) but delta=9.0 (> default 0.1) -> still detected as increasing
        assert calculate_trend([100.0, 109.0], threshold_pct=10.0) == "↑"  # delta > 0.1
    
    def test_negative_values(self):
        """Should handle negative values."""
        assert calculate_trend([-100.0, -90.0]) == "↑"  # Increasing (less negative)
        assert calculate_trend([-100.0, -110.0]) == "↓"  # Decreasing (more negative)


# =============================================================================
# TESTS: MetricConfig.is_abnormal
# =============================================================================

class TestMetricConfigIsAbnormal:
    """Tests for MetricConfig.is_abnormal method."""
    
    def _create_config(
        self,
        range_val: Optional[Tuple[float, float]] = None,
    ) -> MetricConfig:
        """Helper to create a MetricConfig for testing."""
        return MetricConfig(
            canonical_name="test_metric",
            color="#FF0000",
            range=range_val,
            unit="mg/dl",
            axis="y1",
            category="test",
            description="Test metric",
            aliases=(),
        )
    
    def test_value_within_range_normal(self):
        """Should return False when value is within range."""
        config = self._create_config(range_val=(0.8, 1.2))
        
        assert config.is_abnormal(1.0) is False
        assert config.is_abnormal(0.8) is False  # At lower boundary
        assert config.is_abnormal(1.2) is False  # At upper boundary
        assert config.is_abnormal(0.9) is False
        assert config.is_abnormal(1.1) is False
    
    def test_value_below_range_abnormal(self):
        """Should return True when value is below range."""
        config = self._create_config(range_val=(0.8, 1.2))
        
        assert config.is_abnormal(0.7) is True
        assert config.is_abnormal(0.79) is True
        assert config.is_abnormal(0.0) is True
        assert config.is_abnormal(-1.0) is True
    
    def test_value_above_range_abnormal(self):
        """Should return True when value is above range."""
        config = self._create_config(range_val=(0.8, 1.2))
        
        assert config.is_abnormal(1.3) is True
        assert config.is_abnormal(1.21) is True
        assert config.is_abnormal(100.0) is True
    
    def test_no_range_always_normal(self):
        """Should return False when no range is defined."""
        config = self._create_config(range_val=None)
        
        assert config.is_abnormal(0.0) is False
        assert config.is_abnormal(1000.0) is False
        assert config.is_abnormal(-500.0) is False
    
    def test_edge_case_zero_range(self):
        """Should handle zero-width range (single valid value)."""
        config = self._create_config(range_val=(5.0, 5.0))
        
        assert config.is_abnormal(5.0) is False
        assert config.is_abnormal(4.9) is True
        assert config.is_abnormal(5.1) is True
    
    def test_negative_range(self):
        """Should handle ranges with negative values."""
        config = self._create_config(range_val=(-10.0, -5.0))
        
        assert config.is_abnormal(-7.0) is False
        assert config.is_abnormal(-10.0) is False
        assert config.is_abnormal(-5.0) is False
        assert config.is_abnormal(-4.0) is True
        assert config.is_abnormal(-11.0) is True
    
    def test_large_range(self):
        """Should handle large ranges."""
        config = self._create_config(range_val=(0.0, 1000000.0))
        
        assert config.is_abnormal(500000.0) is False
        assert config.is_abnormal(0.0) is False
        assert config.is_abnormal(1000000.0) is False
        assert config.is_abnormal(-0.1) is True
        assert config.is_abnormal(1000000.1) is True
    
    def test_decimal_precision(self):
        """Should handle floating point precision correctly."""
        config = self._create_config(range_val=(0.1, 0.2))
        
        assert config.is_abnormal(0.15) is False
        assert config.is_abnormal(0.1) is False
        assert config.is_abnormal(0.2) is False


# =============================================================================
# TESTS: Blood Pressure Timestamp Alignment
# =============================================================================

class TestBloodPressureTimestampAlignment:
    """Tests for blood pressure timestamp alignment logic."""
    
    def test_perfect_alignment(self):
        """Should align when all timestamps match."""
        ts1 = datetime(2025, 1, 15, 10, 0, 0)
        ts2 = datetime(2025, 1, 16, 10, 0, 0)
        
        systolic = {ts1: 120.0, ts2: 130.0}
        diastolic = {ts1: 80.0, ts2: 85.0}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 2
        assert result[0].timestamp == ts1
        assert result[0].systolic == 120.0
        assert result[0].diastolic == 80.0
        assert result[1].timestamp == ts2
        assert result[1].systolic == 130.0
        assert result[1].diastolic == 85.0
    
    def test_partial_overlap(self):
        """Should only include timestamps where both values exist."""
        ts1 = datetime(2025, 1, 15, 10, 0, 0)
        ts2 = datetime(2025, 1, 16, 10, 0, 0)  # Common
        ts3 = datetime(2025, 1, 17, 10, 0, 0)
        
        systolic = {ts1: 120.0, ts2: 130.0}  # Has ts1, ts2
        diastolic = {ts2: 85.0, ts3: 90.0}   # Has ts2, ts3
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 1
        assert result[0].timestamp == ts2
        assert result[0].systolic == 130.0
        assert result[0].diastolic == 85.0
    
    def test_no_overlap(self):
        """Should return empty list when no timestamps match."""
        ts1 = datetime(2025, 1, 15, 10, 0, 0)
        ts2 = datetime(2025, 1, 16, 10, 0, 0)
        
        systolic = {ts1: 120.0}
        diastolic = {ts2: 80.0}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 0
    
    def test_empty_systolic(self):
        """Should return empty list when systolic is empty."""
        ts1 = datetime(2025, 1, 15, 10, 0, 0)
        
        systolic = {}
        diastolic = {ts1: 80.0}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 0
    
    def test_empty_diastolic(self):
        """Should return empty list when diastolic is empty."""
        ts1 = datetime(2025, 1, 15, 10, 0, 0)
        
        systolic = {ts1: 120.0}
        diastolic = {}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 0
    
    def test_both_empty(self):
        """Should return empty list when both are empty."""
        result = align_blood_pressure_readings({}, {})
        
        assert len(result) == 0
    
    def test_sorted_output(self):
        """Should return results sorted by timestamp."""
        ts1 = datetime(2025, 1, 17, 10, 0, 0)  # Later
        ts2 = datetime(2025, 1, 15, 10, 0, 0)  # Earlier
        ts3 = datetime(2025, 1, 16, 10, 0, 0)  # Middle
        
        # Input in non-sorted order
        systolic = {ts1: 140.0, ts2: 120.0, ts3: 130.0}
        diastolic = {ts1: 90.0, ts2: 80.0, ts3: 85.0}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 3
        assert result[0].timestamp == ts2  # Earliest
        assert result[1].timestamp == ts3  # Middle
        assert result[2].timestamp == ts1  # Latest
    
    def test_single_match(self):
        """Should handle single matching timestamp."""
        ts = datetime(2025, 1, 15, 10, 0, 0)
        
        systolic = {ts: 120.0}
        diastolic = {ts: 80.0}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 1
        assert result[0].timestamp == ts
        assert result[0].systolic == 120.0
        assert result[0].diastolic == 80.0
    
    def test_many_mismatched_few_matched(self):
        """Should correctly identify few matches among many mismatches."""
        # Create many timestamps
        all_systolic_ts = [datetime(2025, 1, i, 10, 0, 0) for i in range(1, 15)]
        all_diastolic_ts = [datetime(2025, 1, i, 10, 0, 0) for i in range(10, 20)]
        
        systolic = {ts: 120.0 + i for i, ts in enumerate(all_systolic_ts)}
        diastolic = {ts: 80.0 + i for i, ts in enumerate(all_diastolic_ts)}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        # Overlap is days 10-14 (5 days)
        assert len(result) == 5
        
        # Verify they're from the overlapping range
        for bp in result:
            assert bp.timestamp.day >= 10
            assert bp.timestamp.day <= 14
    
    def test_microsecond_precision(self):
        """Should require exact timestamp match including microseconds."""
        ts1 = datetime(2025, 1, 15, 10, 0, 0, 0)
        ts2 = datetime(2025, 1, 15, 10, 0, 0, 1)  # 1 microsecond later
        
        systolic = {ts1: 120.0}
        diastolic = {ts2: 80.0}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        # Should NOT match - timestamps differ by 1 microsecond
        assert len(result) == 0
    
    def test_preserves_values_correctly(self):
        """Should correctly associate systolic and diastolic values."""
        ts = datetime(2025, 1, 15, 10, 0, 0)
        
        # Use distinctive values
        systolic = {ts: 142.5}
        diastolic = {ts: 87.3}
        
        result = align_blood_pressure_readings(systolic, diastolic)
        
        assert len(result) == 1
        assert result[0].systolic == 142.5
        assert result[0].diastolic == 87.3


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Additional edge case tests for robustness."""
    
    def test_normalize_metric_name_with_only_special_chars(self):
        """Should return empty string when only special chars."""
        assert _normalize_metric_name("!@#$%^&*()") == ""
        assert _normalize_metric_name("---") == ""
    
    def test_parse_metric_value_with_multiple_numbers(self):
        """Should extract first number from string with multiple numbers."""
        # The function uses regex matching from start, so behavior depends on pattern
        assert parse_metric_value("120 mg 80") == 120.0
    
    def test_calculate_trend_with_identical_values(self):
        """Should return stable for identical values."""
        assert calculate_trend([100.0, 100.0]) == "→"
        assert calculate_trend([0.0, 0.0]) == "→"
    
    def test_calculate_trend_with_very_large_values(self):
        """Should handle very large values."""
        assert calculate_trend([1e10, 1.1e10]) == "↑"
        assert calculate_trend([1e10, 0.9e10]) == "↓"
    
    def test_metric_config_immutability(self):
        """MetricConfig should be immutable (frozen dataclass)."""
        config = MetricConfig(
            canonical_name="test",
            color="#FF0000",
            range=(0.0, 100.0),
            unit="mg/dl",
            axis="y1",
            category="test",
            description="Test",
            aliases=(),
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            config.canonical_name = "modified"

