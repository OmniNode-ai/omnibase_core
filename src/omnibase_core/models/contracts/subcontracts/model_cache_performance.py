"""
Cache Performance Model.

Model for cache performance configuration in the ONEX caching system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCachePerformance(BaseModel):
    """
    Cache performance configuration.

    Defines performance tuning parameters,
    monitoring, and optimization settings.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    max_memory_mb: int = Field(
        default=1024,
        description="Maximum memory allocation for cache",
        ge=1,
    )

    eviction_policy: str = Field(default="lru", description="Cache eviction policy")

    preload_enabled: bool = Field(default=False, description="Enable cache preloading")

    preload_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns for cache preloading",
    )

    compression_enabled: bool = Field(
        default=False,
        description="Enable compression for cached data",
    )

    compression_threshold_bytes: int = Field(
        default=1024,
        description="Minimum size for compression",
        ge=1,
    )

    async_writes: bool = Field(
        default=True,
        description="Enable asynchronous cache writes",
    )

    read_through_enabled: bool = Field(
        default=False,
        description="Enable read-through caching",
    )

    write_through_enabled: bool = Field(
        default=False,
        description="Enable write-through caching",
    )

    write_behind_enabled: bool = Field(
        default=False,
        description="Enable write-behind caching",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
