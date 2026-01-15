"""
Connection pool recommendations model to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field

# Re-export from split module
from omnibase_core.models.configuration.model_pool_performance_profile import (
    ModelPoolPerformanceProfile,
)


class ModelPoolRecommendations(BaseModel):
    """
    Connection pool recommendations with typed fields.
    Replaces Dict[str, Any] for get_pool_recommendations() returns.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

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


__all__ = [
    "ModelPoolPerformanceProfile",  # Re-export from split module
    "ModelPoolRecommendations",
]
