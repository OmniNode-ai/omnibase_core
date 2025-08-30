"""
Monitoring Thresholds Model.

Monitoring and alerting thresholds for priority levels.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelMonitoringThresholds(BaseModel):
    """Monitoring and alerting thresholds for priority levels."""

    # Timing thresholds
    max_queue_time_ms: Optional[int] = Field(
        None, description="Maximum time in queue before alert", ge=1
    )
    max_execution_time_ms: Optional[int] = Field(
        None, description="Maximum execution time before alert", ge=1
    )
    min_response_time_ms: Optional[int] = Field(
        None, description="Minimum expected response time", ge=1
    )

    # Resource thresholds
    max_memory_mb: Optional[int] = Field(
        None, description="Maximum memory usage before alert", ge=1
    )
    max_cpu_percent: Optional[int] = Field(
        None, description="Maximum CPU usage percentage", ge=1, le=100
    )
    max_io_ops_per_second: Optional[int] = Field(
        None, description="Maximum I/O operations per second", ge=1
    )

    # Usage thresholds
    max_daily_usage: Optional[int] = Field(
        None, description="Maximum daily usage count", ge=1
    )
    max_concurrent_executions: Optional[int] = Field(
        None, description="Maximum concurrent executions", ge=1
    )
    cost_alert_threshold: Optional[float] = Field(
        None, description="Cost threshold for alerts", ge=0.0
    )

    # Error thresholds
    max_error_rate_percent: Optional[float] = Field(
        None, description="Maximum error rate percentage", ge=0.0, le=100.0
    )
    max_consecutive_failures: Optional[int] = Field(
        None, description="Maximum consecutive failures before alert", ge=1
    )

    # Alert behavior
    alert_on_failure: bool = Field(True, description="Alert on any execution failure")
    alert_on_timeout: bool = Field(True, description="Alert on execution timeout")
    alert_on_degraded_performance: bool = Field(
        True, description="Alert on performance degradation"
    )
    performance_baseline_factor: float = Field(
        2.0, description="Factor for performance degradation detection", ge=1.0
    )
