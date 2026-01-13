"""
PerformanceBenchmark model.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPerformanceBenchmark(BaseModel):
    """Individual performance benchmark."""

    operation: str = Field(default=..., description="Operation name")
    avg_duration_ms: float = Field(
        default=...,
        description="Average duration in milliseconds",
        ge=0,
    )
    min_duration_ms: float = Field(
        default=...,
        description="Minimum duration in milliseconds",
        ge=0,
    )
    max_duration_ms: float = Field(
        default=...,
        description="Maximum duration in milliseconds",
        ge=0,
    )
    p50_duration_ms: float = Field(
        default=..., description="50th percentile duration", ge=0
    )
    p95_duration_ms: float = Field(
        default=..., description="95th percentile duration", ge=0
    )
    p99_duration_ms: float = Field(
        default=..., description="99th percentile duration", ge=0
    )
    sample_count: int = Field(default=..., description="Number of samples", ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


# Alias
PerformanceBenchmark = ModelPerformanceBenchmark
