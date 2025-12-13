"""
ModelPerformanceOptimizationConfig: Performance optimization configuration.

This model represents performance optimization settings for secret backends.
"""

from pydantic import BaseModel, Field


class ModelPerformanceOptimizationConfig(BaseModel):
    """Performance optimization configuration for secret backends."""

    cache_enabled: bool = Field(default=True, description="Whether caching is enabled")

    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache time-to-live in seconds",
        ge=0,
        le=3600,
    )

    connection_pooling: bool = Field(
        default=False,
        description="Whether connection pooling is enabled",
    )

    max_connections: int = Field(
        default=10,
        description="Maximum number of connections in pool",
        ge=1,
        le=100,
    )

    connection_timeout: int = Field(
        default=5,
        description="Connection timeout in seconds",
        ge=1,
        le=30,
    )
