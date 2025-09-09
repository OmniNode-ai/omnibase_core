"""
Performance Monitoring Subcontract Models for ONEX Nodes.

Provides Pydantic models for metrics collection, performance tracking, and
observability capabilities for all ONEX node types.

Generated from performance_monitoring subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Any

# Import existing enums instead of duplicating
from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of performance metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricUnit(str, Enum):
    """Units for performance metrics."""

    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    BYTES = "bytes"
    MEGABYTES = "megabytes"
    COUNT = "count"
    PERCENT = "percent"
    RATE_PER_SECOND = "rate_per_second"


class ModelMetricValue(BaseModel):
    """A single metric value with metadata."""

    metric_name: str = Field(..., description="Name of the metric")

    value: float = Field(..., description="Numeric value of the metric")

    unit: MetricUnit = Field(..., description="Unit of measurement for the metric")

    timestamp: datetime = Field(..., description="When this metric value was recorded")

    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Labels/tags associated with this metric",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metric metadata",
    )


class ModelMetricsData(BaseModel):
    """Collection of performance metrics."""

    node_type: str = Field(
        ...,
        description="Type of ONEX node (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)",
    )

    node_id: str | None = Field(
        default=None,
        description="Unique identifier for the node instance",
    )

    collection_timestamp: datetime = Field(
        ...,
        description="When these metrics were collected",
    )

    collection_duration_ms: int = Field(
        ...,
        description="Time taken to collect these metrics in milliseconds",
        ge=0,
    )

    metrics: list[ModelMetricValue] = Field(
        default_factory=list,
        description="List of metric values",
    )

    aggregation_period_ms: int = Field(
        default=10000,
        description="Aggregation period for these metrics in milliseconds",
        ge=1000,
    )


class ModelTraceContext(BaseModel):
    """Context information for a performance trace."""

    trace_id: str = Field(..., description="Unique identifier for the trace")

    operation_name: str = Field(..., description="Name of the operation being traced")

    start_time: datetime = Field(..., description="When the trace started")

    parent_trace_id: str | None = Field(
        default=None,
        description="Parent trace ID for nested operations",
    )

    trace_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for the trace",
    )

    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Custom attributes for the trace",
    )


class ModelTraceSummary(BaseModel):
    """Summary of a completed performance trace."""

    trace_id: str = Field(..., description="Unique identifier for the trace")

    operation_name: str = Field(
        ...,
        description="Name of the operation that was traced",
    )

    start_time: datetime = Field(..., description="When the trace started")

    end_time: datetime = Field(..., description="When the trace ended")

    duration_ms: int = Field(
        ...,
        description="Total duration of the operation in milliseconds",
        ge=0,
    )

    success: bool = Field(
        ...,
        description="Whether the traced operation was successful",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if the operation failed",
    )

    performance_metrics: list[ModelMetricValue] = Field(
        default_factory=list,
        description="Performance metrics collected during the trace",
    )

    resource_usage: dict[str, float] = Field(
        default_factory=dict,
        description="Resource usage during the trace (CPU, memory, etc.)",
    )


class ModelPerformanceSummary(BaseModel):
    """Performance summary over a time period."""

    time_range_start: datetime = Field(
        ...,
        description="Start of the time range for this summary",
    )

    time_range_end: datetime = Field(
        ...,
        description="End of the time range for this summary",
    )

    total_operations: int = Field(
        default=0,
        description="Total number of operations in this period",
        ge=0,
    )

    successful_operations: int = Field(
        default=0,
        description="Number of successful operations",
        ge=0,
    )

    failed_operations: int = Field(
        default=0,
        description="Number of failed operations",
        ge=0,
    )

    average_duration_ms: float = Field(
        default=0.0,
        description="Average operation duration in milliseconds",
        ge=0.0,
    )

    p50_duration_ms: float = Field(
        default=0.0,
        description="50th percentile duration in milliseconds",
        ge=0.0,
    )

    p95_duration_ms: float = Field(
        default=0.0,
        description="95th percentile duration in milliseconds",
        ge=0.0,
    )

    p99_duration_ms: float = Field(
        default=0.0,
        description="99th percentile duration in milliseconds",
        ge=0.0,
    )

    throughput_per_second: float = Field(
        default=0.0,
        description="Operations per second",
        ge=0.0,
    )

    error_rate_percent: float = Field(
        default=0.0,
        description="Error rate as percentage",
        ge=0.0,
        le=100.0,
    )


class ModelTrendAnalysis(BaseModel):
    """Trend analysis for performance metrics."""

    metric_name: str = Field(..., description="Name of the metric being analyzed")

    trend_direction: str = Field(
        ...,
        description="Direction of the trend (increasing, decreasing, stable)",
    )

    trend_magnitude: float = Field(
        ...,
        description="Magnitude of the trend (percentage change)",
    )

    confidence_level: float = Field(
        ...,
        description="Confidence level of the trend analysis",
        ge=0.0,
        le=1.0,
    )

    analysis_period_ms: int = Field(
        ...,
        description="Period over which trend was analyzed in milliseconds",
        ge=60000,
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations based on trend analysis",
    )


class ModelAlertConfiguration(BaseModel):
    """Configuration for performance alerts."""

    alert_name: str = Field(..., description="Name of the alert")

    metric_name: str = Field(..., description="Metric to monitor for alerts")

    threshold_value: float = Field(
        ...,
        description="Threshold value that triggers the alert",
    )

    comparison_operator: str = Field(
        ...,
        description="Comparison operator (>, <, >=, <=, ==, !=)",
    )

    severity: AlertSeverity = Field(..., description="Severity level of the alert")

    evaluation_period_ms: int = Field(
        default=60000,
        description="Period over which to evaluate the alert condition",
        ge=10000,
    )

    notification_targets: list[str] = Field(
        default_factory=list,
        description="Targets for alert notifications",
    )

    enabled: bool = Field(default=True, description="Whether the alert is enabled")


class ModelAlertStatus(BaseModel):
    """Current status of performance alerts."""

    alert_name: str = Field(..., description="Name of the alert")

    current_status: str = Field(
        ...,
        description="Current alert status (active, inactive, suppressed)",
    )

    last_triggered: datetime | None = Field(
        default=None,
        description="When the alert was last triggered",
    )

    trigger_count: int = Field(
        default=0,
        description="Number of times the alert has been triggered",
        ge=0,
    )

    current_value: float | None = Field(
        default=None,
        description="Current value of the monitored metric",
    )

    threshold_value: float = Field(..., description="Threshold value for the alert")


# Main subcontract definition model
class ModelPerformanceMonitoringSubcontract(BaseModel):
    """
    Performance Monitoring Subcontract for all ONEX nodes.

    Provides metrics collection, performance tracking, and observability
    capabilities for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.
    """

    subcontract_name: str = Field(
        default="performance_monitoring_subcontract",
        description="Name of the subcontract",
    )

    subcontract_version: str = Field(
        default="1.0.0",
        description="Version of the subcontract",
    )

    applicable_node_types: list[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types this subcontract applies to",
    )

    # Configuration
    collection_interval_ms: int = Field(
        default=10000,
        description="Metrics collection interval in milliseconds",
        ge=1000,
        le=300000,
    )

    metric_retention_hours: int = Field(
        default=168,
        description="How long to retain metrics data in hours",
        ge=1,
        le=8760,
    )

    enable_tracing: bool = Field(
        default=True,
        description="Whether performance tracing is enabled",
    )

    enable_alerts: bool = Field(
        default=True,
        description="Whether performance alerts are enabled",
    )

    max_trace_duration_ms: int = Field(
        default=300000,
        description="Maximum duration for performance traces in milliseconds",
        ge=1000,
        le=3600000,
    )

    aggregation_intervals: list[int] = Field(
        default=[60000, 300000, 3600000],
        description="Aggregation intervals for metrics in milliseconds",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "subcontract_name": "performance_monitoring_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": [
                    "COMPUTE",
                    "EFFECT",
                    "REDUCER",
                    "ORCHESTRATOR",
                ],
                "collection_interval_ms": 10000,
                "metric_retention_hours": 168,
                "enable_tracing": True,
                "enable_alerts": True,
                "max_trace_duration_ms": 300000,
                "aggregation_intervals": [60000, 300000, 3600000],
            },
        }
