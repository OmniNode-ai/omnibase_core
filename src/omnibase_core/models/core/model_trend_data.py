"""
Trend data model to replace Dict[str, Any] usage for trends fields.
"""

from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.core.model_trend_metrics import ModelTrendMetrics
from omnibase_core.models.core.model_trend_point import ModelTrendPoint

# Compatibility aliases
TrendPoint = ModelTrendPoint
TrendMetrics = ModelTrendMetrics


class ModelTrendData(BaseModel):
    """
    Trend data with typed fields.
    Replaces Dict[str, Any] for trends fields.
    """

    # Trend identification
    trend_name: str = Field(default=..., description="Trend identifier")
    trend_type: str = Field(
        default=..., description="Type of trend (metric/usage/performance)"
    )
    time_period: str = Field(
        default=...,
        description="Time period (hourly/daily/weekly/monthly)",
    )

    # Data points
    data_points: list[ModelTrendPoint] = Field(
        default_factory=list,
        description="Trend data points",
    )

    # Analysis
    metrics: ModelTrendMetrics | None = Field(
        default=None,
        description="Trend analysis metrics",
    )

    # Metadata
    unit: str | None = Field(default=None, description="Unit of measurement")
    data_source: str | None = Field(default=None, description="Data source")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update time",
    )

    # Forecast (optional)
    forecast_points: list[ModelTrendPoint] | None = Field(
        default=None,
        description="Forecasted data points",
    )
    confidence_interval: float | None = Field(
        default=None,
        description="Forecast confidence interval",
    )

    # Anomalies
    anomaly_points: list[ModelTrendPoint] | None = Field(
        default=None,
        description="Detected anomaly points",
    )
    anomaly_threshold: float | None = Field(
        default=None,
        description="Anomaly detection threshold",
    )

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, object] | None) -> "ModelTrendData | None":
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        # Pydantic validates the data at runtime - type safety is enforced by Pydantic
        return cls.model_validate(dict(data))

    def add_point(
        self,
        timestamp: datetime,
        value: float | int,
        label: str | None = None,
    ) -> None:
        """Add a new data point to the trend."""
        self.data_points.append(
            ModelTrendPoint(timestamp=timestamp, value=value, label=label),
        )

    def calculate_metrics(self) -> None:
        """Calculate trend metrics from data points."""
        if not self.data_points:
            return

        values = [p.value for p in self.data_points]
        self.metrics = ModelTrendMetrics(
            min_value=min(values),
            max_value=max(values),
            avg_value=sum(values) / len(values),
            median_value=sorted(values)[len(values) // 2],
            trend_direction=self._calculate_trend_direction(values),
            change_percent=self._calculate_change_percent(values),
        )

    def _calculate_trend_direction(self, values: list[float | int]) -> str:
        """Calculate overall trend direction."""
        if len(values) < 2:
            return "stable"

        first_half_avg = sum(values[: len(values) // 2]) / (len(values) // 2)
        second_half_avg = sum(values[len(values) // 2 :]) / (
            len(values) - len(values) // 2
        )

        if second_half_avg > first_half_avg * 1.05:
            return "up"
        if second_half_avg < first_half_avg * 0.95:
            return "down"
        return "stable"

    def _calculate_change_percent(
        self,
        values: list[float | int],
    ) -> float | None:
        """Calculate percentage change from start to end."""
        if len(values) < 2 or values[0] == 0:
            return None
        return ((values[-1] - values[0]) / values[0]) * 100

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
