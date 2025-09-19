"""
Caching configuration model for nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumCacheEvictionPolicy


class ModelCachingConfig(BaseModel):
    """Caching configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Whether caching is enabled",
    )
    ttl_seconds: int = Field(
        default=300,
        description="Cache TTL in seconds",
        ge=0,
    )
    max_size: int = Field(
        default=1000,
        description="Maximum cache size",
        ge=1,
    )
    eviction_policy: EnumCacheEvictionPolicy = Field(
        default=EnumCacheEvictionPolicy.LRU,
        description="Cache eviction policy",
    )
