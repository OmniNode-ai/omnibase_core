"""
Performance metrics for a node collection.

Provides aggregated performance data for collections including invocation
counts, popularity scores, and documentation coverage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCollectionPerformanceMetrics(BaseModel):
    """Performance metrics for a collection."""

    model_config = ConfigDict(extra="forbid")

    total_invocations: int = Field(
        default=0,
        description="Total node invocations across collection",
        ge=0,
    )
    avg_popularity_score: float = Field(
        default=0.0,
        description="Average popularity score",
        ge=0.0,
        le=100.0,
    )
    documentation_coverage: float = Field(
        default=0.0,
        description="Documentation coverage percentage",
        ge=0.0,
        le=100.0,
    )
