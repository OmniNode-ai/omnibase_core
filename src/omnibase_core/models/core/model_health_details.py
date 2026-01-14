"""
Model for health check details.

Structured model for health check details, replacing Dict[str, Any]
with proper typing for health details.
"""

from pydantic import BaseModel, Field


class ModelHealthDetails(BaseModel):
    """
    Structured model for health check details.

    Replaces Dict[str, Any] with proper typing for health details.
    """

    service_name: str | None = Field(default=None, description="Service name")
    endpoint_status: str | None = Field(default=None, description="Endpoint status")
    database_connection: bool | None = Field(
        default=None,
        description="Database connection status",
    )
    external_services: bool | None = Field(
        default=None,
        description="External services status",
    )
    disk_usage_percent: float | None = Field(
        default=None,
        description="Disk usage percentage",
    )
    active_connections: int | None = Field(
        default=None,
        description="Number of active connections",
    )
    error_level_count: int | None = Field(
        default=None, description="Number of recent errors"
    )
    last_backup: str | None = Field(default=None, description="Last backup timestamp")
    queue_depth: int | None = Field(default=None, description="Message queue depth")
    response_time_ms: float | None = Field(
        default=None,
        description="Average response time in milliseconds",
    )
