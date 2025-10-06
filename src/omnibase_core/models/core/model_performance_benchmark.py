from pydantic import Field

"""
PerformanceBenchmark model.
"""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class ModelPerformanceBenchmark(BaseModel):
    """Individual performance benchmark."""

    operation: str = Field(..., description="Operation name")
    avg_duration_ms: float = Field(
        ...,
        description="Average duration in milliseconds",
        ge=0,
    )
    min_duration_ms: float = Field(
        ...,
        description="Minimum duration in milliseconds",
        ge=0,
    )
    max_duration_ms: float = Field(
        ...,
        description="Maximum duration in milliseconds",
        ge=0,
    )
    p50_duration_ms: float = Field(..., description="50th percentile duration", ge=0)
    p95_duration_ms: float = Field(..., description="95th percentile duration", ge=0)
    p99_duration_ms: float = Field(..., description="99th percentile duration", ge=0)
    sample_count: int = Field(..., description="Number of samples", ge=1)

    model_config = ConfigDict()


# Alias
PerformanceBenchmark = ModelPerformanceBenchmark
