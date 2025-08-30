"""
Connection pool recommendations model to replace Dict[str, Any] usage.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelPoolRecommendations(BaseModel):
    """
    Connection pool recommendations with typed fields.
    Replaces Dict[str, Any] for get_pool_recommendations() returns.
    """

    # Recommended settings
    recommended_pool_size: int = Field(..., description="Recommended pool size")
    recommended_max_overflow: int = Field(..., description="Recommended max overflow")
    recommended_pool_timeout: int = Field(
        ..., description="Recommended pool timeout (seconds)"
    )
    recommended_pool_recycle: int = Field(
        ..., description="Recommended pool recycle time (seconds)"
    )

    # Current vs recommended analysis
    current_pool_size: Optional[int] = Field(None, description="Current pool size")
    pool_size_delta: Optional[int] = Field(
        None, description="Difference from recommended"
    )

    # Reasoning
    recommendations: List[str] = Field(
        default_factory=list, description="Specific recommendations"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Configuration warnings"
    )

    # Performance impact
    expected_connection_wait_reduction: Optional[float] = Field(
        None, description="Expected wait time reduction percentage"
    )
    expected_throughput_increase: Optional[float] = Field(
        None, description="Expected throughput increase percentage"
    )

    # Resource impact
    memory_impact_mb: Optional[float] = Field(
        None, description="Additional memory usage in MB"
    )
    connection_overhead: Optional[int] = Field(
        None, description="Additional database connections"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)
