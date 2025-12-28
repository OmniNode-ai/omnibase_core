"""
Cache settings model.
"""

from pydantic import BaseModel, Field

from omnibase_core.constants import DEFAULT_CACHE_TTL_SECONDS


class ModelCacheSettings(BaseModel):
    """
    Cache settings with typed fields.
    Replaces Dict[str, Any] for get_cache_settings() returns.
    """

    # Basic settings
    enabled: bool = Field(default=True, description="Whether caching is enabled")
    cache_type: str = Field(
        default="memory", description="Cache type (memory/redis/disk)"
    )

    # TTL settings
    default_ttl_seconds: int = Field(
        default=DEFAULT_CACHE_TTL_SECONDS, description="Default TTL in seconds"
    )
    max_ttl_seconds: int | None = Field(
        default=3600, description="Maximum TTL in seconds"
    )

    # Size limits
    max_size_mb: int | None = Field(default=100, description="Maximum cache size in MB")
    max_entries: int | None = Field(
        default=1000, description="Maximum number of entries"
    )

    # Eviction policy
    eviction_policy: str = Field(
        default="LRU", description="Eviction policy (LRU/LFU/FIFO)"
    )

    # Performance settings
    compression_enabled: bool = Field(default=False, description="Enable compression")
    compression_level: int = Field(default=6, description="Compression level (1-9)")

    # Cache key settings
    key_prefix: str | None = Field(default=None, description="Cache key prefix")
    key_hash_algorithm: str = Field(
        default="sha256", description="Key hashing algorithm"
    )

    # Invalidation
    invalidation_enabled: bool = Field(
        default=True, description="Enable cache invalidation"
    )
    invalidation_patterns: list[str] = Field(
        default_factory=list,
        description="Invalidation patterns",
    )

    # Statistics
    track_statistics: bool = Field(default=True, description="Track cache statistics")
    statistics_interval_seconds: int = Field(
        default=60,
        description="Statistics collection interval",
    )

    def get_effective_ttl(self, requested_ttl: int | None = None) -> int:
        """Get effective TTL considering limits."""
        if not self.enabled:
            return 0

        ttl = requested_ttl or self.default_ttl_seconds
        if self.max_ttl_seconds:
            ttl = min(ttl, self.max_ttl_seconds)

        return max(0, ttl)
