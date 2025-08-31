"""
Cache settings model.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelCacheSettings(BaseModel):
    """
    Cache settings with typed fields.
    Replaces Dict[str, Any] for get_cache_settings() returns.
    """

    # Basic settings
    enabled: bool = Field(True, description="Whether caching is enabled")
    cache_type: str = Field("memory", description="Cache type (memory/redis/disk)")

    # TTL settings
    default_ttl_seconds: int = Field(300, description="Default TTL in seconds")
    max_ttl_seconds: int | None = Field(3600, description="Maximum TTL in seconds")

    # Size limits
    max_size_mb: int | None = Field(100, description="Maximum cache size in MB")
    max_entries: int | None = Field(1000, description="Maximum number of entries")

    # Eviction policy
    eviction_policy: str = Field("LRU", description="Eviction policy (LRU/LFU/FIFO)")

    # Performance settings
    compression_enabled: bool = Field(False, description="Enable compression")
    compression_level: int = Field(6, description="Compression level (1-9)")

    # Cache key settings
    key_prefix: str | None = Field(None, description="Cache key prefix")
    key_hash_algorithm: str = Field("md5", description="Key hashing algorithm")

    # Invalidation
    invalidation_enabled: bool = Field(True, description="Enable cache invalidation")
    invalidation_patterns: list[str] = Field(
        default_factory=list,
        description="Invalidation patterns",
    )

    # Statistics
    track_statistics: bool = Field(True, description="Track cache statistics")
    statistics_interval_seconds: int = Field(
        60,
        description="Statistics collection interval",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    def get_effective_ttl(self, requested_ttl: int | None = None) -> int:
        """Get effective TTL considering limits."""
        if not self.enabled:
            return 0

        ttl = requested_ttl or self.default_ttl_seconds
        if self.max_ttl_seconds:
            ttl = min(ttl, self.max_ttl_seconds)

        return max(0, ttl)
