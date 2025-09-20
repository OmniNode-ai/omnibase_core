"""
Trend data model to replace Dict[str, Any] usage for trends fields.

Strongly typed model with UUID identification, enum support, validation,
and comprehensive trend analysis capabilities.
"""

from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from ...enums.enum_trend_direction import EnumTrendDirection
from ...enums.enum_trend_type import EnumTrendType
from ...enums.enum_time_period import EnumTimePeriod
from .model_trend_metrics import ModelTrendMetrics
from .model_trend_point import ModelTrendPoint

# Compatibility aliases
TrendPoint = ModelTrendPoint
TrendMetrics = ModelTrendMetrics


class ModelTrendData(BaseModel):
    """
    Strongly typed trend data with comprehensive analysis capabilities.
    Replaces Dict[str, Any] for trends fields with full type safety.
    """

    # Unique identification
    trend_id: UUID = Field(default_factory=uuid4, description="Unique trend identifier")

    # Trend identification
    trend_name: str = Field(..., min_length=1, description="Trend identifier name")
    trend_type: EnumTrendType = Field(..., description="Type of trend pattern")
    time_period: EnumTimePeriod = Field(..., description="Time period for trend analysis")

    # Data points with validation
    data_points: list[ModelTrendPoint] = Field(
        default_factory=list,
        description="Trend data points",
    )

    # Analysis results
    metrics: ModelTrendMetrics | None = Field(
        None,
        description="Calculated trend analysis metrics",
    )

    # Quality and confidence
    overall_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in trend analysis (0.0-1.0)",
    )
    data_quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Data quality score (0.0-1.0)",
    )

    # Metadata
    unit: str | None = Field(None, description="Unit of measurement")
    data_source: str | None = Field(None, description="Data source identifier")
    tags: list[str] = Field(default_factory=list, description="Classification tags")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update time",
    )

    # Forecast capabilities
    forecast_points: list[ModelTrendPoint] = Field(
        default_factory=list,
        description="Forecasted data points",
    )
    forecast_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Forecast confidence level (0.0-1.0)",
    )
    forecast_horizon_days: int = Field(
        default=0,
        ge=0,
        description="Forecast horizon in days",
    )

    # Anomaly detection
    anomaly_points: list[ModelTrendPoint] = Field(
        default_factory=list,
        description="Detected anomaly points",
    )
    anomaly_threshold: float = Field(
        default=2.0,
        ge=0.0,
        description="Anomaly detection threshold (standard deviations)",
    )
    anomaly_sensitivity: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Anomaly detection sensitivity (0.0-1.0)",
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional trend metadata",
    )

    model_config = ConfigDict()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ModelTrendData"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)

    @field_validator("trend_name")
    @classmethod
    def validate_trend_name(cls, v: str) -> str:
        """Validate trend name is not empty."""
        if not v.strip():
            raise ValueError("Trend name cannot be empty")
        return v.strip()

    @field_validator("data_points")
    @classmethod
    def validate_data_points(cls, v: list[ModelTrendPoint]) -> list[ModelTrendPoint]:
        """Validate data points are sorted by timestamp."""
        if len(v) > 1:
            timestamps = [point.timestamp for point in v]
            if timestamps != sorted(timestamps):
                # Sort the points by timestamp
                v.sort(key=lambda point: point.timestamp)
        return v

    @model_validator(mode='after')
    def validate_forecast_consistency(self) -> 'ModelTrendData':
        """Validate forecast-related fields are consistent."""
        if self.forecast_points:
            if self.forecast_confidence == 0.0:
                object.__setattr__(self, 'forecast_confidence', 0.5)  # Default confidence

            if self.forecast_horizon_days == 0 and self.forecast_points:
                # Calculate horizon from forecast points
                if self.data_points:
                    last_data = max(self.data_points, key=lambda p: p.timestamp)
                    first_forecast = min(self.forecast_points, key=lambda p: p.timestamp)
                    horizon = (first_forecast.timestamp - last_data.timestamp).days
                    object.__setattr__(self, 'forecast_horizon_days', max(1, horizon))

        return self

    def add_point(
        self,
        timestamp: datetime,
        value: float,
        confidence: float = 1.0,
        quality_score: float = 1.0,
        label: str | None = None,
        **kwargs: Any
    ) -> None:
        """Add a new data point to the trend."""
        new_point = ModelTrendPoint(
            timestamp=timestamp,
            value=value,
            confidence=confidence,
            quality_score=quality_score,
            label=label,
            **kwargs
        )
        self.data_points.append(new_point)
        # Keep data points sorted by timestamp
        self.data_points.sort(key=lambda p: p.timestamp)

    def calculate_metrics(self) -> None:
        """Calculate comprehensive trend metrics from data points."""
        if not self.data_points:
            return

        # Get reliable data points only
        reliable_points = [p for p in self.data_points if p.is_reliable()]
        if not reliable_points:
            reliable_points = self.data_points  # Use all if none are reliable

        values = [p.value for p in reliable_points]
        weighted_values = [p.get_weighted_value() for p in reliable_points]

        # Calculate trend direction using enum
        trend_direction = self._calculate_trend_direction(values)

        # Use ModelTrendMetrics.calculate_from_values for consistency
        self.metrics = ModelTrendMetrics.calculate_from_values(
            values=values,
            trend_direction=trend_direction,
            trend_type=self.trend_type,
            confidence_level=self._calculate_overall_confidence(reliable_points),
            sample_size=len(reliable_points),
            time_span_days=self._calculate_time_span_days(),
        )

        # Update overall confidence and quality
        self.overall_confidence = self.metrics.confidence_level
        self.data_quality_score = self._calculate_data_quality_score(reliable_points)

    def _calculate_trend_direction(self, values: list[float]) -> EnumTrendDirection:
        """Calculate overall trend direction using strongly typed enum."""
        if len(values) < 2:
            return EnumTrendDirection.FLAT

        # Calculate percentage change
        change_percent = self._calculate_change_percent(values)

        # Calculate volatility
        if len(values) > 2:
            avg = sum(values) / len(values)
            variance = sum((x - avg) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            volatility = std_dev / avg if avg != 0 else 0

            # High volatility threshold
            if volatility > 0.2:  # 20% volatility
                return EnumTrendDirection.SIDEWAYS

        # Use change percent to determine direction
        if change_percent > 5.0:
            return EnumTrendDirection.UP
        elif change_percent < -5.0:
            return EnumTrendDirection.DOWN
        elif abs(change_percent) > 2.0:
            # Check for breakout pattern
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]

            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0

            if second_avg > first_avg * 1.1:  # 10% increase
                return EnumTrendDirection.UPWARD_BREAKOUT
            elif second_avg < first_avg * 0.9:  # 10% decrease
                return EnumTrendDirection.DOWNWARD_BREAKOUT

        return EnumTrendDirection.FLAT

    def _calculate_change_percent(self, values: list[float]) -> float:
        """Calculate percentage change from start to end."""
        if len(values) < 2 or values[0] == 0:
            return 0.0
        return ((values[-1] - values[0]) / values[0]) * 100

    def _calculate_overall_confidence(self, points: list[ModelTrendPoint]) -> float:
        """Calculate overall confidence from data points."""
        if not points:
            return 0.0

        confidences = [p.confidence for p in points]
        quality_scores = [p.quality_score for p in points]

        # Weighted average of confidence and quality
        avg_confidence = sum(confidences) / len(confidences)
        avg_quality = sum(quality_scores) / len(quality_scores)

        return (avg_confidence + avg_quality) / 2

    def _calculate_data_quality_score(self, points: list[ModelTrendPoint]) -> float:
        """Calculate overall data quality score."""
        if not points:
            return 0.0

        # Base quality from individual points
        base_quality = sum(p.quality_score for p in points) / len(points)

        # Adjust for completeness (fewer gaps = higher quality)
        completeness_factor = 1.0 - (sum(1 for p in points if p.is_interpolated) / len(points))

        # Adjust for anomalies (fewer anomalies = higher quality)
        anomaly_factor = 1.0 - (sum(1 for p in points if p.is_anomaly) / len(points))

        return base_quality * completeness_factor * anomaly_factor

    def _calculate_time_span_days(self) -> float:
        """Calculate time span of the trend data in days."""
        if len(self.data_points) < 2:
            return 0.0

        timestamps = [p.timestamp for p in self.data_points]
        time_span = max(timestamps) - min(timestamps)
        return time_span.total_seconds() / 86400  # Convert to days

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()

    @field_serializer("trend_id")
    def serialize_uuid(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)

    def get_high_quality_points(self) -> list[ModelTrendPoint]:
        """Get only high quality data points."""
        return [p for p in self.data_points if p.is_high_quality()]

    def get_reliable_points(self) -> list[ModelTrendPoint]:
        """Get only reliable data points."""
        return [p for p in self.data_points if p.is_reliable()]

    def detect_anomalies(self) -> list[ModelTrendPoint]:
        """Detect anomaly points based on statistical analysis."""
        if len(self.data_points) < 3:
            return []

        reliable_points = self.get_reliable_points()
        if len(reliable_points) < 3:
            reliable_points = self.data_points

        values = [p.value for p in reliable_points]
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5

        anomalies = []
        for point in self.data_points:
            z_score = abs(point.value - avg) / std_dev if std_dev > 0 else 0
            if z_score > self.anomaly_threshold:
                # Mark as anomaly and add to list
                point.is_anomaly = True
                anomalies.append(point)

        # Update anomaly_points list
        self.anomaly_points = anomalies
        return anomalies

    def is_trending_up(self) -> bool:
        """Check if trend is moving upward."""
        if not self.metrics:
            return False
        return EnumTrendDirection.is_positive(self.metrics.trend_direction)

    def is_trending_down(self) -> bool:
        """Check if trend is moving downward."""
        if not self.metrics:
            return False
        return EnumTrendDirection.is_negative(self.metrics.trend_direction)

    def is_stable(self) -> bool:
        """Check if trend is stable."""
        if not self.metrics:
            return False
        return EnumTrendDirection.is_neutral(self.metrics.trend_direction)

    def has_breakout(self) -> bool:
        """Check if trend shows breakout pattern."""
        if not self.metrics:
            return False
        return EnumTrendDirection.is_breakout(self.metrics.trend_direction)

    def get_trend_summary(self) -> dict[str, Any]:
        """Get a comprehensive trend summary."""
        return {
            "trend_id": str(self.trend_id),
            "trend_name": self.trend_name,
            "trend_type": self.trend_type.value,
            "time_period": self.time_period.value,
            "direction": self.metrics.trend_direction.value if self.metrics else "unknown",
            "change_percent": self.metrics.change_percent if self.metrics else 0.0,
            "confidence": self.overall_confidence,
            "quality_score": self.data_quality_score,
            "data_points_count": len(self.data_points),
            "anomalies_count": len(self.anomaly_points),
            "forecasts_count": len(self.forecast_points),
            "is_significant": self.metrics.is_significant_trend() if self.metrics else False,
            "is_high_confidence": self.metrics.is_high_confidence() if self.metrics else False,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def create_from_values(
        cls,
        trend_name: str,
        values: list[float],
        timestamps: list[datetime],
        trend_type: EnumTrendType = EnumTrendType.LINEAR,
        time_period: EnumTimePeriod = EnumTimePeriod.DAY,
        **kwargs: Any
    ) -> "ModelTrendData":
        """Create trend data from value and timestamp lists."""
        if len(values) != len(timestamps):
            raise ValueError("Values and timestamps must have same length")

        if not values:
            raise ValueError("Cannot create trend from empty values")

        # Create data points
        data_points = [
            ModelTrendPoint(timestamp=ts, value=val, label=None, source=None)
            for ts, val in zip(timestamps, values)
        ]

        # Sort by timestamp
        data_points.sort(key=lambda p: p.timestamp)

        # Create trend data
        trend_data = cls(
            trend_name=trend_name,
            trend_type=trend_type,
            time_period=time_period,
            data_points=data_points,
            **kwargs
        )

        # Calculate metrics
        trend_data.calculate_metrics()

        return trend_data
