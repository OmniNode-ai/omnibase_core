"""
Service Status Model.

Status of a system service.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelServiceStatus(BaseModel):
    """Status of a system service."""

    service_name: str = Field(..., description="Name of the service")
    service_type: Optional[str] = Field(None, description="Type of service")
    status: str = Field(..., description="Service status (running, stopped, error)")
    health: Optional[str] = Field(
        None, description="Service health (healthy, degraded, unhealthy)"
    )

    # Service details
    version: Optional[str] = Field(None, description="Service version")
    uptime_seconds: Optional[int] = Field(None, description="Service uptime")
    last_check: Optional[str] = Field(None, description="Last health check timestamp")

    # Performance metrics
    response_time_ms: Optional[float] = Field(None, description="Average response time")
    error_rate: Optional[float] = Field(None, description="Error rate percentage")
    request_count: Optional[int] = Field(None, description="Total request count")

    # Additional info
    message: Optional[str] = Field(None, description="Status message")
    details: Optional[Dict[str, str]] = Field(None, description="Additional details")
