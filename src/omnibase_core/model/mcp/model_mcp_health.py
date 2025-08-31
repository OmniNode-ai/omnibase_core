"""
Model for MCP server health check response.
"""

from pydantic import BaseModel, Field


class ModelMCPHealth(BaseModel):
    """Model for MCP server health status."""

    status: str = Field(description="Health status (healthy, degraded, unhealthy)")
    service: str = Field(description="Service name")
    timestamp: float = Field(description="Unix timestamp")
    uptime_seconds: float = Field(description="Service uptime in seconds")
