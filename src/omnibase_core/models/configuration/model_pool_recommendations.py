from pydantic import Field

"""
Connection pool recommendations model to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel


class ModelPoolPerformanceProfile(BaseModel):
    """Driver-specific performance profile for connection pools."""

    recommended_pool_size: int = Field(
        default=10, description="Recommended pool size for this driver"
    )
    recommended_max_overflow: int = Field(
        default=20, description="Recommended max overflow for this driver"
    )
    connection_overhead: str = Field(
        default="medium", description="Connection overhead level (low/medium/high)"
    )
    concurrent_connections_limit: int = Field(
        default=100, description="Maximum concurrent connections supported"
    )


class ModelPoolRecommendations(BaseModel):
    """
    Connection pool recommendations with typed fields.
    Replaces Dict[str, Any] for get_pool_recommendations() returns.
    """

    # Recommended settings
    recommended_pool_size: int = Field(default=..., description="Recommended pool size")
    recommended_max_overflow: int = Field(
        default=..., description="Recommended max overflow"
    )
    recommended_pool_timeout: int = Field(
        default=...,
        description="Recommended pool timeout (seconds)",
    )
    recommended_pool_recycle: int = Field(
        default=...,
        description="Recommended pool recycle time (seconds)",
    )

    # Current vs recommended analysis
    current_pool_size: int | None = Field(default=None, description="Current pool size")
    pool_size_delta: int | None = Field(
        default=None,
        description="Difference from recommended",
    )

    # Reasoning
    recommendations: list[str] = Field(
        default_factory=list,
        description="Specific recommendations",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Configuration warnings",
    )

    # Performance impact
    expected_connection_wait_reduction: float | None = Field(
        default=None,
        description="Expected wait time reduction percentage",
    )
    expected_throughput_increase: float | None = Field(
        default=None,
        description="Expected throughput increase percentage",
    )

    # Resource impact
    memory_impact_mb: float | None = Field(
        default=None,
        description="Additional memory usage in MB",
    )
    connection_overhead: int | None = Field(
        default=None,
        description="Additional database connections",
    )

    # Performance profile
    performance_profile: ModelPoolPerformanceProfile | None = Field(
        default=None,
        description="Driver-specific performance profile",
    )
