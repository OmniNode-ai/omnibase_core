"""
Monitoring metrics model to replace Dict[str, Any] usage for metrics.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.discovery.model_metric_value import (
    AnyMetricValue,
    ModelMetricValue,
)
from omnibase_core.types.type_serializable_value import SerializedDict

# Compatibility alias
MetricValue = ModelMetricValue


class ModelMonitoringMetrics(BaseModel):
    """
    Monitoring metrics container with typed fields.
    Replaces Dict[str, Any] for get_monitoring_metrics() returns.
    """

    # Performance metrics
    response_time_ms: float | None = Field(
        default=None,
        description="Response time in milliseconds",
    )
    throughput_rps: float | None = Field(
        default=None,
        description="Throughput in requests per second",
    )
    error_rate: float | None = Field(default=None, description="Error rate percentage")
    success_rate: float | None = Field(
        default=None, description="Success rate percentage"
    )

    # Resource utilization
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )
    disk_usage_gb: float | None = Field(default=None, description="Disk usage in GB")
    network_bandwidth_mbps: float | None = Field(
        default=None,
        description="Network bandwidth in Mbps",
    )

    # Queue/processing metrics
    queue_depth: int | None = Field(default=None, description="Current queue depth")
    items_processed: int | None = Field(
        default=None, description="Total items processed"
    )
    items_failed: int | None = Field(default=None, description="Total items failed")
    processing_lag_ms: float | None = Field(
        default=None,
        description="Processing lag in milliseconds",
    )

    # Health indicators
    health_score: float | None = Field(
        default=None,
        description="Overall health score (0-100)",
    )
    compliance_score: float | None = Field(
        default=None,
        description="Compliance score (0-100)",
    )
    reliability_score: float | None = Field(
        default=None,
        description="Reliability score (0-100)",
    )
    availability_percent: float | None = Field(
        default=None,
        description="Service availability percentage",
    )
    uptime_seconds: int | None = Field(
        default=None, description="Service uptime in seconds"
    )
    last_error_timestamp: datetime | None = Field(
        default=None,
        description="Last error occurrence",
    )

    # Custom metrics (for extensibility)
    custom_metrics: dict[str, AnyMetricValue] | None = Field(
        default_factory=dict,
        description="Custom metrics with values",
    )

    # Time window
    start_time: datetime | None = Field(
        default=None, description="Metrics window start"
    )
    end_time: datetime | None = Field(default=None, description="Metrics window end")
    collection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When metrics were collected",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @classmethod
    def from_dict(cls, data: SerializedDict) -> "ModelMonitoringMetrics":
        """Create from dictionary for easy migration."""
        return cls.model_validate(data)

    @field_serializer(
        "last_error_timestamp",
        "start_time",
        "end_time",
        "collection_timestamp",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
