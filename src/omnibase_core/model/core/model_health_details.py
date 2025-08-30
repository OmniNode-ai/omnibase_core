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

    service_name: str | None = Field(None, description="Service name")
    endpoint_status: str | None = Field(None, description="Endpoint status")
    database_connection: bool | None = Field(
        None,
        description="Database connection status",
    )
    external_services: bool | None = Field(
        None,
        description="External services status",
    )
    disk_usage_percent: float | None = Field(
        None,
        description="Disk usage percentage",
    )
    active_connections: int | None = Field(
        None,
        description="Number of active connections",
    )
    error_count: int | None = Field(None, description="Number of recent errors")
    last_backup: str | None = Field(None, description="Last backup timestamp")
    queue_depth: int | None = Field(None, description="Message queue depth")
    response_time_ms: float | None = Field(
        None,
        description="Average response time in milliseconds",
    )
