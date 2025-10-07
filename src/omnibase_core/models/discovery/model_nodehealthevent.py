from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.constants.event_types import NODE_HEALTH_EVENT
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.health.model_health_metrics import ModelHealthMetrics


class ModelNodeHealthEvent(ModelOnexEvent):
    """
    Event published by nodes to update their health status.

    This event allows nodes to regularly report their health metrics
    to the registry, enabling health-based service discovery and
    monitoring.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=NODE_HEALTH_EVENT,
        description="Event type identifier",
    )

    # Node identification
    node_name: str = Field(default=..., description="Name of the node reporting health")

    # Health information
    health_metrics: ModelHealthMetrics = Field(
        default=...,
        description="Current health metrics for the node",
    )

    # Reporting metadata
    report_interval_seconds: int | None = Field(
        default=None,
        description="How often this node reports health (for scheduling)",
    )
    next_report_time: datetime | None = Field(
        default=None,
        description="When the next health report is expected",
    )

    # Consul compatibility
    service_id: str | None = Field(
        default=None,
        description="Service ID for Consul health checks",
    )
    check_id: str | None = Field(default=None, description="Health check ID for Consul")

    @classmethod
    def create_healthy_report(
        cls,
        node_id: UUID,
        node_name: str,
        uptime_seconds: int | None = None,
        response_time_ms: float | None = None,
        **kwargs: Any,
    ) -> "ModelNodeHealthEvent":
        """
        Factory method to create a healthy status report.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            uptime_seconds: Node uptime
            response_time_ms: Average response time
            **kwargs: Additional fields

        Returns:
            ModelNodeHealthEvent for healthy status
        """
        health_metrics = ModelHealthMetrics(
            cpu_usage_percent=10.0,  # Low CPU usage
            memory_usage_percent=20.0,  # Low memory usage
            response_time_ms=response_time_ms or 50.0,
            error_rate=0.0,  # No errors
            success_rate=100.0,  # Perfect success rate
            uptime_seconds=uptime_seconds or 0,
            consecutive_errors=0,
            custom_metrics={"status": 1.0},  # 1.0 = healthy
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    @classmethod
    def create_warning_report(
        cls,
        node_id: UUID,
        node_name: str,
        warning_reason: str,
        cpu_usage: float | None = None,
        memory_usage: float | None = None,
        error_rate: float | None = None,
        **kwargs: Any,
    ) -> "ModelNodeHealthEvent":
        """
        Factory method to create a warning status report.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            warning_reason: Reason for warning status
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            error_rate: Error rate percentage
            **kwargs: Additional fields

        Returns:
            ModelNodeHealthEvent for warning status
        """
        health_metrics = ModelHealthMetrics(
            cpu_usage_percent=cpu_usage or 85.0,  # High CPU usage
            memory_usage_percent=memory_usage or 85.0,  # High memory usage
            error_rate=error_rate or 5.0,  # Elevated error rate
            success_rate=95.0,  # Reduced success rate
            response_time_ms=500.0,  # Slower response
            consecutive_errors=2,  # Some consecutive errors
            custom_metrics={
                "status": 0.5,  # 0.5 = warning
                "warning_code": hash(warning_reason) % 1000 / 1000.0,
            },
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    @classmethod
    def create_critical_report(
        cls,
        node_id: UUID,
        node_name: str,
        error_message: str,
        **kwargs: Any,
    ) -> "ModelNodeHealthEvent":
        """
        Factory method to create a critical status report.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            error_message: Critical error message
            **kwargs: Additional fields

        Returns:
            ModelNodeHealthEvent for critical status
        """
        health_metrics = ModelHealthMetrics(
            cpu_usage_percent=95.0,  # Critical CPU usage
            memory_usage_percent=95.0,  # Critical memory usage
            error_rate=50.0,  # High error rate
            success_rate=50.0,  # Low success rate
            response_time_ms=2000.0,  # Very slow response
            consecutive_errors=10,  # Many consecutive errors
            last_error_timestamp=datetime.now(),
            custom_metrics={
                "status": 0.0,  # 0.0 = critical
                "error_code": hash(error_message) % 1000 / 1000.0,
            },
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    def is_healthy(self) -> bool:
        """Check if the node is healthy"""
        # Use ModelHealthMetrics.is_healthy() method
        return self.health_metrics.is_healthy()

    def needs_attention(self) -> bool:
        """Check if the node needs attention (warning or critical)"""
        # Node needs attention if it's not healthy
        return not self.health_metrics.is_healthy()
