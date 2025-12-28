"""
Data preparation service for health record visualization.

Responsible for:
- Grouping records by metric type
- Parsing timestamps and values
- Computing abnormal flags
- Returning normalized dataset structures

This service is visualization-agnostic and prepares data
that can be consumed by any visualization backend.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from api.schemas import HealthRecordResponse
from services.graph.metric_registry import (
    MetricConfig,
    get_metric_config,
    parse_timestamp,
    parse_metric_value,
    calculate_trend,
    format_metric_value,
    DEFAULT_VISIBLE_METRICS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# NORMALIZED DATA STRUCTURES
# =============================================================================

@dataclass
class MetricDataPoint:
    """A single validated data point for a metric."""
    timestamp: datetime
    value: float
    is_abnormal: bool


@dataclass
class PreparedMetricData:
    """
    Prepared data for a single metric type, ready for visualization.
    
    Contains all parsed/validated data points plus metadata.
    """
    metric_name: str
    config: MetricConfig
    unit: str
    data_points: List[MetricDataPoint] = field(default_factory=list)
    
    @property
    def timestamps(self) -> List[datetime]:
        """Extract all timestamps as a list."""
        return [dp.timestamp for dp in self.data_points]
    
    @property
    def values(self) -> List[float]:
        """Extract all values as a list."""
        return [dp.value for dp in self.data_points]
    
    @property
    def is_abnormal(self) -> List[bool]:
        """Extract all abnormal flags as a list."""
        return [dp.is_abnormal for dp in self.data_points]
    
    def is_empty(self) -> bool:
        """Check if there are no valid data points."""
        return len(self.data_points) == 0


@dataclass
class BloodPressureDataPoint:
    """A single blood pressure reading with both systolic and diastolic."""
    timestamp: datetime
    systolic: float
    diastolic: float


@dataclass
class PreparedBloodPressureData:
    """
    Prepared blood pressure data with aligned systolic/diastolic readings.
    
    Blood pressure readings are only included when both systolic and
    diastolic values exist at the same timestamp to ensure medical accuracy.
    """
    data_points: List[BloodPressureDataPoint] = field(default_factory=list)
    
    @property
    def timestamps(self) -> List[datetime]:
        """Extract all timestamps as a list."""
        return [dp.timestamp for dp in self.data_points]
    
    @property
    def systolic_values(self) -> List[float]:
        """Extract all systolic values as a list."""
        return [dp.systolic for dp in self.data_points]
    
    @property
    def diastolic_values(self) -> List[float]:
        """Extract all diastolic values as a list."""
        return [dp.diastolic for dp in self.data_points]
    
    def is_empty(self) -> bool:
        """Check if there are no valid data points."""
        return len(self.data_points) == 0


@dataclass
class MetricSummary:
    """Summary information for a single metric."""
    metric_name: str
    config: MetricConfig
    latest_value: float
    latest_timestamp: datetime
    unit: str
    is_abnormal: bool
    trend: str  # "↑", "↓", "→", or ""
    formatted_value: str


@dataclass
class PreparedDataset:
    """
    Complete prepared dataset for visualization.
    
    Contains all metrics, blood pressure data, and summary information
    in a normalized, visualization-ready format.
    """
    metrics: Dict[str, PreparedMetricData]
    blood_pressure: Optional[PreparedBloodPressureData]
    summaries: List[MetricSummary]
    visible_metrics: List[str]
    date_range: Tuple[datetime, datetime]
    
    def get_all_timestamps(self) -> List[datetime]:
        """Get all timestamps across all metrics."""
        all_timestamps: List[datetime] = []
        for metric_data in self.metrics.values():
            all_timestamps.extend(metric_data.timestamps)
        if self.blood_pressure:
            all_timestamps.extend(self.blood_pressure.timestamps)
        return all_timestamps


# =============================================================================
# DATA PREPARATION SERVICE
# =============================================================================

class DataPreparationService:
    """
    Service for preparing health record data for visualization.
    
    Handles all data parsing, validation, and normalization independently
    of any visualization library. The prepared data structures can be
    consumed by any visualization backend (Plotly, matplotlib, etc.).
    """

    def prepare_dataset(
        self,
        records: List[HealthRecordResponse],
    ) -> PreparedDataset:
        """
        Prepare a complete dataset from health records.
        
        Args:
            records: List of health record responses to prepare
            
        Returns:
            PreparedDataset with all metrics normalized and validated
        """
        if not records:
            now = datetime.now()
            return PreparedDataset(
                metrics={},
                blood_pressure=None,
                summaries=[],
                visible_metrics=[],
                date_range=(now, now),
            )

        # Group records by metric type
        records_by_type = self._group_records_by_type(records)
        
        # Prepare blood pressure data (if both systolic and diastolic exist)
        blood_pressure = self._prepare_blood_pressure(records_by_type)
        
        # Remove BP components from standard metrics if BP was prepared
        if blood_pressure and not blood_pressure.is_empty():
            records_by_type.pop('systolic', None)
            records_by_type.pop('diastolic', None)
        
        # Prepare all other metrics
        prepared_metrics: Dict[str, PreparedMetricData] = {}
        for metric_name, type_records in records_by_type.items():
            prepared = self._prepare_metric_data(metric_name, type_records)
            if not prepared.is_empty():
                prepared_metrics[metric_name] = prepared
        
        # Determine visible metrics
        available_metrics = list(prepared_metrics.keys())
        visible_metrics = self._determine_visible_metrics(available_metrics)
        
        # Calculate date range
        date_range = self._calculate_date_range(prepared_metrics, blood_pressure)
        
        # Prepare summaries
        summaries = self._prepare_summaries(prepared_metrics)
        
        return PreparedDataset(
            metrics=prepared_metrics,
            blood_pressure=blood_pressure,
            summaries=summaries,
            visible_metrics=visible_metrics,
            date_range=date_range,
        )

    def _group_records_by_type(
        self,
        records: List[HealthRecordResponse],
    ) -> Dict[str, List[HealthRecordResponse]]:
        """Group records by their normalized metric type."""
        records_by_type: Dict[str, List[HealthRecordResponse]] = defaultdict(list)
        for record in records:
            normalized_type = record.record_type.lower()
            records_by_type[normalized_type].append(record)
        return dict(records_by_type)

    def _prepare_metric_data(
        self,
        metric_name: str,
        records: List[HealthRecordResponse],
    ) -> PreparedMetricData:
        """
        Prepare data for a single metric type.
        
        Filters out records with unparseable timestamps or values.
        """
        sorted_records = sorted(records, key=lambda x: x.timestamp)
        config = get_metric_config(metric_name)
        
        # Determine unit from first record or fallback to config
        unit = ''
        if sorted_records and sorted_records[0].unit:
            unit = sorted_records[0].unit
        else:
            unit = config.unit
        
        data_points: List[MetricDataPoint] = []
        
        for record in sorted_records:
            ts = parse_timestamp(record.timestamp, record_id=getattr(record, 'id', None))
            if ts is None:
                continue
            
            parsed_value = parse_metric_value(record.value, metric_name)
            if parsed_value is None:
                continue
            
            is_abnormal = config.is_abnormal(parsed_value)
            
            data_points.append(MetricDataPoint(
                timestamp=ts,
                value=parsed_value,
                is_abnormal=is_abnormal,
            ))
        
        return PreparedMetricData(
            metric_name=metric_name,
            config=config,
            unit=unit,
            data_points=data_points,
        )

    def _prepare_blood_pressure(
        self,
        records_by_type: Dict[str, List[HealthRecordResponse]],
    ) -> Optional[PreparedBloodPressureData]:
        """
        Prepare blood pressure data with aligned systolic/diastolic readings.
        
        Blood pressure readings are only included when BOTH systolic and
        diastolic values exist at the exact same timestamp, ensuring
        medical accuracy.
        """
        if 'systolic' not in records_by_type or 'diastolic' not in records_by_type:
            return None
        
        sys_records = records_by_type['systolic']
        dia_records = records_by_type['diastolic']
        
        # Build timestamp-keyed mappings
        systolic_by_ts: Dict[datetime, float] = {}
        diastolic_by_ts: Dict[datetime, float] = {}
        
        for record in sys_records:
            ts = parse_timestamp(record.timestamp, record_id=getattr(record, 'id', None))
            if ts is None:
                continue
            val = parse_metric_value(record.value, 'systolic')
            if val is not None:
                systolic_by_ts[ts] = val
        
        for record in dia_records:
            ts = parse_timestamp(record.timestamp, record_id=getattr(record, 'id', None))
            if ts is None:
                continue
            val = parse_metric_value(record.value, 'diastolic')
            if val is not None:
                diastolic_by_ts[ts] = val
        
        # Find timestamps where BOTH values exist
        common_timestamps = sorted(set(systolic_by_ts.keys()) & set(diastolic_by_ts.keys()))
        
        if not common_timestamps:
            if systolic_by_ts or diastolic_by_ts:
                logger.warning(
                    "Blood pressure data incomplete: no timestamps with both systolic and diastolic values",
                    extra={
                        'systolic_count': len(systolic_by_ts),
                        'diastolic_count': len(diastolic_by_ts)
                    }
                )
            return PreparedBloodPressureData(data_points=[])
        
        data_points = [
            BloodPressureDataPoint(
                timestamp=ts,
                systolic=systolic_by_ts[ts],
                diastolic=diastolic_by_ts[ts],
            )
            for ts in common_timestamps
        ]
        
        return PreparedBloodPressureData(data_points=data_points)

    def _determine_visible_metrics(
        self,
        available_metrics: List[str],
    ) -> List[str]:
        """Determine which metrics to show by default (max 3)."""
        visible: List[str] = []
        
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

    def _calculate_date_range(
        self,
        metrics: Dict[str, PreparedMetricData],
        blood_pressure: Optional[PreparedBloodPressureData],
    ) -> Tuple[datetime, datetime]:
        """Calculate the date range across all data."""
        all_timestamps: List[datetime] = []
        
        for metric_data in metrics.values():
            all_timestamps.extend(metric_data.timestamps)
        
        if blood_pressure:
            all_timestamps.extend(blood_pressure.timestamps)
        
        if all_timestamps:
            return (min(all_timestamps), max(all_timestamps))
        
        now = datetime.now()
        return (now, now)

    def _prepare_summaries(
        self,
        metrics: Dict[str, PreparedMetricData],
    ) -> List[MetricSummary]:
        """
        Prepare summary information for each metric.
        
        Returns summaries sorted by clinical priority.
        """
        # Priority order for summary display
        priority = (
            'creatinine', 'blood urea', 'random blood sugar',
            'haemoglobin', 'sodium', 'potassium'
        )
        
        # Sort metrics: priority first, then alphabetically
        sorted_metric_names: List[str] = []
        for p in priority:
            for metric_name in metrics:
                config = get_metric_config(metric_name)
                if (metric_name == p or config.canonical_name == p) and metric_name not in sorted_metric_names:
                    sorted_metric_names.append(metric_name)
                    break
        for metric_name in sorted(metrics.keys()):
            if metric_name not in sorted_metric_names:
                sorted_metric_names.append(metric_name)
        
        summaries: List[MetricSummary] = []
        
        for metric_name in sorted_metric_names[:5]:
            metric_data = metrics.get(metric_name)
            if not metric_data or metric_data.is_empty():
                continue
            
            # Get latest data point
            latest_dp = metric_data.data_points[-1]
            
            # Calculate trend from values
            values = metric_data.values
            trend = calculate_trend(values)
            
            summaries.append(MetricSummary(
                metric_name=metric_name,
                config=metric_data.config,
                latest_value=latest_dp.value,
                latest_timestamp=latest_dp.timestamp,
                unit=metric_data.unit,
                is_abnormal=latest_dp.is_abnormal,
                trend=trend,
                formatted_value=format_metric_value(latest_dp.value),
            ))
        
        return summaries

