"""
Node Health Event Model

Event published by nodes to update their health status in the registry.
Enables real-time health monitoring in service discovery.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.core.constants.event_types import CoreEventTypes
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.discovery.model_custom_metrics import ModelCustomMetrics


class ModelHealthMetrics(BaseModel):
    """Health metrics for a node"""

    # Basic health status
    status: str = Field(
        ...,
        description="Health status (healthy, warning, critical, unknown)",
    )

    # Performance metrics
    cpu_usage_percent: float | None = Field(
        None,
        description="CPU usage percentage (0-100)",
    )
    memory_usage_percent: float | None = Field(
        None,
        description="Memory usage percentage (0-100)",
    )
    response_time_ms: float | None = Field(
        None,
        description="Average response time in milliseconds",
    )

    # Operational metrics
    uptime_seconds: int | None = Field(None, description="Node uptime in seconds")
    error_rate: float | None = Field(
        None,
        description="Error rate percentage (0-100)",
    )
    request_count: int | None = Field(None, description="Total requests processed")

    # Health check details
    health_check_url: str | None = Field(
        None,
        description="URL for health check endpoint",
    )
    last_health_check: datetime | None = Field(
        None,
        description="When the last health check was performed",
    )
    health_check_duration_ms: float | None = Field(
        None,
        description="Duration of last health check in milliseconds",
    )

    # Custom metrics
    custom_metrics: ModelCustomMetrics = Field(
        default_factory=ModelCustomMetrics,
        description="Additional custom health metrics",
    )


class ModelNodeHealthEvent(ModelOnexEvent):
    """
    Event published by nodes to update their health status.

    This event allows nodes to regularly report their health metrics
    to the registry, enabling health-based service discovery and
    monitoring.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=CoreEventTypes.NODE_HEALTH_EVENT,
        description="Event type identifier",
    )

    # Node identification
    node_name: str = Field(..., description="Name of the node reporting health")

    # Health information
    health_metrics: ModelHealthMetrics = Field(
        ...,
        description="Current health metrics for the node",
    )

    # Reporting metadata
    report_interval_seconds: int | None = Field(
        None,
        description="How often this node reports health (for scheduling)",
    )
    next_report_time: datetime | None = Field(
        None,
        description="When the next health report is expected",
    )

    # Consul compatibility
    service_id: str | None = Field(
        None,
        description="Service ID for Consul health checks",
    )
    check_id: str | None = Field(None, description="Health check ID for Consul")

    @classmethod
    def create_healthy_report(
        cls,
        node_id: str,
        node_name: str,
        uptime_seconds: int | None = None,
        response_time_ms: float | None = None,
        **kwargs,
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
            status="healthy",
            uptime_seconds=uptime_seconds,
            response_time_ms=response_time_ms,
            last_health_check=datetime.now(),
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
        node_id: str,
        node_name: str,
        warning_reason: str,
        cpu_usage: float | None = None,
        memory_usage: float | None = None,
        error_rate: float | None = None,
        **kwargs,
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
            status="warning",
            cpu_usage_percent=cpu_usage,
            memory_usage_percent=memory_usage,
            error_rate=error_rate,
            last_health_check=datetime.now(),
            custom_metrics=ModelCustomMetrics.from_dict(
                {"warning_reason": warning_reason},
            ),
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
        node_id: str,
        node_name: str,
        error_message: str,
        **kwargs,
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
            status="critical",
            last_health_check=datetime.now(),
            custom_metrics=ModelCustomMetrics.from_dict(
                {"error_message": error_message},
            ),
        )

        return cls(
            node_id=node_id,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    def is_healthy(self) -> bool:
        """Check if the node is healthy"""
        return self.health_metrics.status == "healthy"

    def needs_attention(self) -> bool:
        """Check if the node needs attention (warning or critical)"""
        return self.health_metrics.status in ["warning", "critical"]
