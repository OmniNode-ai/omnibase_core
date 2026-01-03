from datetime import datetime
from typing import Any, cast
from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.constants.constants_event_types import NODE_HEALTH_EVENT
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.health.model_health_metrics import ModelHealthMetrics
from omnibase_core.utils.util_hash import deterministic_error_code
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelNodeHealthEvent(ModelOnexEvent):
    """
    Event published by nodes to update their health status.

    This event allows nodes to regularly report their health metrics
    to the registry, enabling health-based service discovery and
    monitoring.
    """

    event_type: str = Field(
        default=NODE_HEALTH_EVENT, description="Event type identifier"
    )
    node_name: str = Field(default=..., description="Name of the node reporting health")
    health_metrics: ModelHealthMetrics = Field(
        default=..., description="Current health metrics for the node"
    )
    report_interval_seconds: int | None = Field(
        default=None, description="How often this node reports health (for scheduling)"
    )
    next_report_time: datetime | None = Field(
        default=None, description="When the next health report is expected"
    )
    service_id: UUID | None = Field(
        default=None, description="Service ID for Consul health checks"
    )
    check_id: UUID | None = Field(
        default=None, description="Health check ID for Consul"
    )

    @field_validator("node_id", mode="before")
    @classmethod
    def convert_node_id_to_uuid(cls, v: Any) -> UUID:
        """Convert string node_id to UUID if needed."""
        if isinstance(v, str):
            return uuid_from_string(v, namespace="node")
        return cast("UUID", v)

    @field_validator("health_metrics", mode="before")
    @classmethod
    def convert_health_metrics(cls, v: Any) -> ModelHealthMetrics:
        """Convert dict-like or simple health metrics to ModelHealthMetrics."""
        if isinstance(v, ModelHealthMetrics):
            return v

        # Handle dict or object with 'status' field (test compatibility)
        if hasattr(v, "status") or (isinstance(v, dict) and "status" in v):
            status = v.status if hasattr(v, "status") else v.get("status")
            cpu = (
                v.cpu_usage_percent
                if hasattr(v, "cpu_usage_percent")
                else v.get("cpu_usage_percent", 0.0)
            )
            memory = (
                v.memory_usage_percent
                if hasattr(v, "memory_usage_percent")
                else v.get("memory_usage_percent", 0.0)
            )
            uptime = (
                v.uptime_seconds
                if hasattr(v, "uptime_seconds")
                else v.get("uptime_seconds", 0)
            )

            # Create ModelHealthMetrics with appropriate defaults based on status
            return ModelHealthMetrics(
                cpu_usage_percent=cpu,
                memory_usage_percent=memory,
                uptime_seconds=uptime,
                custom_metrics={"status": status},
            )

        return cast("ModelHealthMetrics", v)

    @classmethod
    def create_healthy_report(
        cls,
        node_id: UUID | str,
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
        # Convert node_id to UUID if it's a string
        node_uuid = (
            uuid_from_string(node_id, namespace="node")
            if isinstance(node_id, str)
            else node_id
        )

        health_metrics = ModelHealthMetrics(
            cpu_usage_percent=10.0,
            memory_usage_percent=20.0,
            response_time_ms=response_time_ms or 50.0,
            error_rate=0.0,
            success_rate=100.0,
            uptime_seconds=uptime_seconds or 0,
            consecutive_errors=0,
            custom_metrics={"status": 1.0},
        )
        return cls(
            node_id=node_uuid,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    @classmethod
    def create_warning_report(
        cls,
        node_id: UUID | str,
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
        # Convert node_id to UUID if it's a string
        node_uuid = (
            uuid_from_string(node_id, namespace="node")
            if isinstance(node_id, str)
            else node_id
        )

        health_metrics = ModelHealthMetrics(
            cpu_usage_percent=cpu_usage or 85.0,
            memory_usage_percent=memory_usage or 85.0,
            error_rate=error_rate or 5.0,
            success_rate=95.0,
            response_time_ms=500.0,
            consecutive_errors=2,
            custom_metrics={
                "status": "warning",
                "warning_reason": warning_reason,
            },
        )
        return cls(
            node_id=node_uuid,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    @classmethod
    def create_critical_report(
        cls, node_id: UUID | str, node_name: str, error_message: str, **kwargs: Any
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
        # Convert node_id to UUID if it's a string
        node_uuid = (
            uuid_from_string(node_id, namespace="node")
            if isinstance(node_id, str)
            else node_id
        )

        health_metrics = ModelHealthMetrics(
            cpu_usage_percent=95.0,
            memory_usage_percent=95.0,
            error_rate=50.0,
            success_rate=50.0,
            response_time_ms=2000.0,
            consecutive_errors=10,
            last_error_timestamp=datetime.now(),
            custom_metrics={
                "status": 0.0,
                # Use deterministic hash for consistent error codes across Python sessions
                "error_code": deterministic_error_code(error_message),
            },
        )
        return cls(
            node_id=node_uuid,
            node_name=node_name,
            health_metrics=health_metrics,
            **kwargs,
        )

    def is_healthy(self) -> bool:
        """Check if the node is healthy"""
        return self.health_metrics.is_healthy()

    def needs_attention(self) -> bool:
        """Check if the node needs attention (warning or critical)"""
        return not self.health_metrics.is_healthy()
