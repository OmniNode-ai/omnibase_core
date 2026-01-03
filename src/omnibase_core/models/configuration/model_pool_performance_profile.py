"""
Pool Performance Profile Model.

Driver-specific performance profile for connection pools.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPoolPerformanceProfile(BaseModel):
    """Driver-specific performance profile for connection pools."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

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


__all__ = ["ModelPoolPerformanceProfile"]
