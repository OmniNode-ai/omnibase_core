"""
ModelHealthMetric - Health metrics tracking model

Health metric model for tracking specific measurable health indicators
with thresholds, trends, and temporal tracking.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ModelHealthMetric(BaseModel):
    """
    Health metric model for tracking measurable health indicators

    This model tracks individual health metrics including current values,
    thresholds, trend analysis, and temporal tracking.
    """

    metric_name: str = Field(
        default=...,
        description="Metric name (e.g., 'cpu_usage', 'memory_usage', 'response_time')",
    )

    current_value: float = Field(default=..., description="Current metric value")

    unit: str = Field(
        default=..., description="Metric unit (e.g., '%', 'ms', 'MB', 'req/s')"
    )

    threshold_warning: float | None = Field(
        default=None,
        description="Warning threshold value",
    )

    threshold_critical: float | None = Field(
        default=None,
        description="Critical threshold value",
    )

    trend: str = Field(
        default="stable",
        description="Metric trend direction",
        pattern="^(improving|stable|degrading|unknown)$",
    )

    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last metric update timestamp",
    )

    min_value: float | None = Field(default=None, description="Minimum recorded value")

    max_value: float | None = Field(default=None, description="Maximum recorded value")

    average_value: float | None = Field(
        default=None,
        description="Average value over time period",
    )

    def is_warning(self) -> bool:
        """Check if metric value exceeds warning threshold"""
        if self.threshold_warning is None:
            return False
        return self.current_value >= self.threshold_warning

    def is_critical(self) -> bool:
        """Check if metric value exceeds critical threshold"""
        if self.threshold_critical is None:
            return False
        return self.current_value >= self.threshold_critical

    def is_degrading(self) -> bool:
        """Check if metric trend is degrading"""
        return self.trend == "degrading"

    def get_formatted_value(self) -> str:
        """Get formatted metric value with unit"""
        return f"{self.current_value:.2f}{self.unit}"

    def get_status(self) -> str:
        """Get overall metric status"""
        if self.is_critical():
            return "critical"
        if self.is_warning():
            return "warning"
        if self.is_degrading():
            return "degrading"
        return "normal"

    def update_value(self, new_value: float) -> None:
        """Update metric with new value and recalculate stats"""
        old_value = self.current_value
        self.current_value = new_value
        self.last_updated = datetime.now(UTC)

        # Update min/max
        if self.min_value is None or new_value < self.min_value:
            self.min_value = new_value
        if self.max_value is None or new_value > self.max_value:
            self.max_value = new_value

        # Update trend
        if new_value > old_value:
            self.trend = (
                "improving"
                if self.metric_name in ["response_time", "error_rate", "memory_usage"]
                else "degrading"
            )
        elif new_value < old_value:
            self.trend = (
                "degrading"
                if self.metric_name in ["response_time", "error_rate", "memory_usage"]
                else "improving"
            )
        else:
            self.trend = "stable"

    @classmethod
    def create_cpu_metric(cls, value: float) -> "ModelHealthMetric":
        """Create a CPU usage metric"""
        return cls(
            metric_name="cpu_usage",
            current_value=value,
            unit="%",
            threshold_warning=80.0,
            threshold_critical=95.0,
        )

    @classmethod
    def create_memory_metric(cls, value: float) -> "ModelHealthMetric":
        """Create a memory usage metric"""
        return cls(
            metric_name="memory_usage",
            current_value=value,
            unit="%",
            threshold_warning=85.0,
            threshold_critical=95.0,
        )

    @classmethod
    def create_response_time_metric(cls, value: float) -> "ModelHealthMetric":
        """Create a response time metric"""
        return cls(
            metric_name="response_time",
            current_value=value,
            unit="ms",
            threshold_warning=1000.0,
            threshold_critical=5000.0,
        )
