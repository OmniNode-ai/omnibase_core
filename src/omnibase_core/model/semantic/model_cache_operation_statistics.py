"""
Cache operation statistics model.

Provides strongly-typed cache statistics to replace Dict[str, Any] usage.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelCacheOperationStatistics(BaseModel):
    """
    Statistics about cache operations.

    Replaces Dict[str, Any] usage in cache_statistics fields.
    """

    total_requests: int = Field(default=0, description="Total number of cache requests")

    cache_hits: int = Field(default=0, description="Number of cache hits")

    cache_misses: int = Field(default=0, description="Number of cache misses")

    hit_ratio: Optional[float] = Field(
        default=None, description="Cache hit ratio (0-1)"
    )

    memory_cache_hits: int = Field(default=0, description="Hits from memory cache")

    postgres_cache_hits: int = Field(
        default=0, description="Hits from PostgreSQL cache"
    )

    average_lookup_time_ms: Optional[float] = Field(
        default=None, description="Average cache lookup time in milliseconds"
    )

    average_storage_time_ms: Optional[float] = Field(
        default=None, description="Average cache storage time in milliseconds"
    )

    total_entries_stored: int = Field(
        default=0, description="Total number of entries stored in session"
    )

    total_entries_evicted: int = Field(
        default=0, description="Total number of entries evicted"
    )

    memory_usage_bytes: Optional[int] = Field(
        default=None, description="Current memory usage by cache in bytes"
    )

    disk_usage_bytes: Optional[int] = Field(
        default=None, description="Current disk usage by cache in bytes"
    )

    compression_ratio: Optional[float] = Field(
        default=None, description="Compression ratio achieved (0-1)"
    )

    expired_entries_cleaned: int = Field(
        default=0, description="Number of expired entries cleaned up"
    )

    duplicate_requests_deduplicated: int = Field(
        default=0, description="Number of duplicate requests served from cache"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
