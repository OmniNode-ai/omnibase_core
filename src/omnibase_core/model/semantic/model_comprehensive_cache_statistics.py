"""Comprehensive cache statistics model with strong typing."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.semantic.model_cache_config import ModelCacheConfig
from omnibase_core.model.semantic.model_cache_statistics import ModelCacheStatistics


class ModelRedisCacheStatistics(BaseModel):
    """Redis cache statistics model."""

    connected: bool = Field(description="Whether Redis is connected")
    enabled: bool | None = Field(
        default=None,
        description="Whether Redis cache is enabled",
    )
    used_memory: str | None = Field(default=None, description="Redis memory usage")
    keyspace_hits: int | None = Field(
        default=None,
        ge=0,
        description="Redis keyspace hits",
    )
    keyspace_misses: int | None = Field(
        default=None,
        ge=0,
        description="Redis keyspace misses",
    )
    error: str | None = Field(default=None, description="Connection error if any")

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelCachePerformanceStatistics(BaseModel):
    """Cache performance statistics model."""

    total_queries: int = Field(ge=0, description="Total queries processed")
    cache_saves: int = Field(ge=0, description="Number of cache saves")
    memory_hit_rate: float = Field(ge=0.0, le=1.0, description="Memory cache hit rate")
    redis_hit_rate: float = Field(ge=0.0, le=1.0, description="Redis cache hit rate")
    overall_hit_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall cache hit rate",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelComprehensiveCacheStatistics(BaseModel):
    """Comprehensive cache statistics model."""

    config: ModelCacheConfig = Field(description="Cache configuration")
    memory_cache: ModelCacheStatistics = Field(description="Memory cache statistics")
    redis_cache: ModelRedisCacheStatistics = Field(description="Redis cache statistics")
    performance: ModelCachePerformanceStatistics = Field(
        description="Performance statistics",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
