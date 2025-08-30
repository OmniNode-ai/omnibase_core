"""Cache statistics model with strong typing."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelCacheStatistics(BaseModel):
    """Strongly typed cache statistics model."""

    size: int = Field(ge=0, description="Current cache size")
    capacity: int = Field(ge=0, description="Maximum cache capacity")
    expired_entries: int = Field(ge=0, description="Number of expired entries")
    utilization: float = Field(ge=0.0, le=1.0, description="Cache utilization ratio")
    hit_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Cache hit rate"
    )
    miss_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Cache miss rate"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
