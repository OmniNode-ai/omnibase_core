"""
Caching Configuration Model.

Caching strategy and policies defining caching behavior for expensive computations
with TTL, size limits, and eviction policies.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCachingConfig(BaseModel):
    """
    Caching strategy and policies.

    Defines caching behavior for expensive computations
    with TTL, size limits, and eviction policies.
    """

    strategy: str = Field(
        default="lru",
        description="Caching strategy (lru, fifo, lfu)",
    )

    max_size: int = Field(
        default=1000,
        description="Maximum cache size (number of entries)",
        ge=1,
    )

    ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cache entries in seconds",
        ge=1,
    )

    enabled: bool = Field(default=True, description="Enable caching")

    cache_key_strategy: str = Field(
        default="input_hash",
        description="Strategy for generating cache keys",
    )

    eviction_policy: str = Field(
        default="least_recently_used",
        description="Eviction policy when cache is full",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
