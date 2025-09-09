"""
Monitoring metrics model to replace Dict[str, Any] usage for metrics.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.model.core.model_metric_value import ModelMetricValue

# Backward compatibility alias
MetricValue = ModelMetricValue

class ModelMonitoringMetrics(BaseModel):
    """
    Monitoring metrics container with typed fields.
    Replaces Dict[str, Any] for get_monitoring_metrics() returns.
    """

    # Performance metrics
    response_time_ms: float | None = Field(
        None,
        description="Response time in milliseconds",
    )
    throughput_rps: float | None = Field(
        None,
        description="Throughput in requests per second",
    )
    error_rate: float | None = Field(None, description="Error rate percentage")
    success_rate: float | None = Field(None, description="Success rate percentage")

    # Resource utilization
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    disk_usage_gb: float | None = Field(None, description="Disk usage in GB")
    network_bandwidth_mbps: float | None = Field(
        None,
        description="Network bandwidth in Mbps",
    )

    # Queue/processing metrics
    queue_depth: int | None = Field(None, description="Current queue depth")
    items_processed: int | None = Field(None, description="Total items processed")
    items_failed: int | None = Field(None, description="Total items failed")
    processing_lag_ms: float | None = Field(
        None,
        description="Processing lag in milliseconds",
    )

    # Health indicators
    health_score: float | None = Field(
        None,
        description="Overall health score (0-100)",
    )
    availability_percent: float | None = Field(
        None,
        description="Service availability percentage",
    )
    uptime_seconds: int | None = Field(None, description="Service uptime in seconds")
    last_error_timestamp: datetime | None = Field(
        None,
        description="Last error occurrence",
    )

    # Custom metrics (for extensibility)
    custom_metrics: dict[str, ModelMetricValue] | None = Field(
        default_factory=dict,
        description="Custom metrics with values",
    )

    # Time window
    start_time: datetime | None = Field(None, description="Metrics window start")
    end_time: datetime | None = Field(None, description="Metrics window end")
    collection_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When metrics were collected",
    )

    model_config = ConfigDict()
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelMonitoringMetrics":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @field_serializer(
        "last_error_timestamp",
        "start_time",
        "end_time",
        "collection_timestamp",
    )
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
