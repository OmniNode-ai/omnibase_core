from pydantic import Field

__all__ = [
    "ModelHealthMetrics",
    "ModelNodeHealthEvent",
]

"""
Node Health Event Model

Event published by nodes to update their health status in the registry.
Enables real-time health monitoring in service discovery.
"""

from datetime import datetime

from pydantic import BaseModel

from omnibase_core.models.discovery.model_custom_metrics import ModelCustomMetrics

from .model_nodehealthevent import ModelNodeHealthEvent


class ModelHealthMetrics(BaseModel):
    """Health metrics for a node"""

    # Basic health status
    status: str = Field(
        default=...,
        description="Health status (healthy, warning, critical, unknown)",
    )

    # Performance metrics
    cpu_usage_percent: float | None = Field(
        default=None,
        description="CPU usage percentage (0-100)",
    )
    memory_usage_percent: float | None = Field(
        default=None,
        description="Memory usage percentage (0-100)",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Average response time in milliseconds",
    )

    # Operational metrics
    uptime_seconds: int | None = Field(
        default=None, description="Node uptime in seconds"
    )
    error_rate: float | None = Field(
        default=None,
        description="Error rate percentage (0-100)",
    )
    request_count: int | None = Field(
        default=None, description="Total requests processed"
    )

    # Health check details
    health_check_url: str | None = Field(
        default=None,
        description="URL for health check endpoint",
    )
    last_health_check: datetime | None = Field(
        default=None,
        description="When the last health check was performed",
    )
    health_check_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Duration of last health check in milliseconds",
    )

    # Custom metrics
    custom_metrics: ModelCustomMetrics = Field(
        default_factory=ModelCustomMetrics,
        description="Additional custom health metrics",
    )
