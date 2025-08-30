"""
Model for health check details.

Structured model for health check details, replacing Dict[str, Any]
with proper typing for health details.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelHealthDetails(BaseModel):
    """
    Structured model for health check details.

    Replaces Dict[str, Any] with proper typing for health details.
    """

    service_name: Optional[str] = Field(None, description="Service name")
    endpoint_status: Optional[str] = Field(None, description="Endpoint status")
    database_connection: Optional[bool] = Field(
        None, description="Database connection status"
    )
    external_services: Optional[bool] = Field(
        None, description="External services status"
    )
    disk_usage_percent: Optional[float] = Field(
        None, description="Disk usage percentage"
    )
    active_connections: Optional[int] = Field(
        None, description="Number of active connections"
    )
    error_count: Optional[int] = Field(None, description="Number of recent errors")
    last_backup: Optional[str] = Field(None, description="Last backup timestamp")
    queue_depth: Optional[int] = Field(None, description="Message queue depth")
    response_time_ms: Optional[float] = Field(
        None, description="Average response time in milliseconds"
    )
