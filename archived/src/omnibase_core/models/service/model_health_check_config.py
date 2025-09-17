"""
Health check configuration model for service monitoring.
"""

from pydantic import BaseModel, Field


class ModelHealthCheckConfig(BaseModel):
    """Health check configuration for service monitoring."""

    enabled: bool = Field(True, description="Enable health checks")
    interval_seconds: int = Field(
        30,
        description="Health check interval in seconds",
        ge=1,
        le=300,
    )
    timeout_seconds: int = Field(
        10,
        description="Health check timeout in seconds",
        ge=1,
        le=60,
    )
    retries: int = Field(3, description="Number of health check retries", ge=1, le=10)
    start_period_seconds: int = Field(
        60,
        description="Grace period before health checks start",
        ge=0,
        le=300,
    )
    endpoint: str = Field("/health", description="Health check endpoint path")
