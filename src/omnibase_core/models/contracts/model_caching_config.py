from pydantic import Field

"""
Caching Configuration Model - ONEX Standards Compliant.

Caching strategy and policies defining caching behavior for expensive computations
with TTL, size limits, and eviction policies.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
