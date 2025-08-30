"""
Query cache models for OmniMemory performance optimization.

Provides strongly typed models for caching query results with timestamps.
"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for cached data
T = TypeVar("T")


class ModelCacheEntry(BaseModel, Generic[T]):
    """Generic cache entry with timestamp for TTL management."""

    cache_key: str = Field(..., description="Unique key for the cache entry")
    cached_data: T = Field(..., description="The cached data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the entry was cached"
    )
    ttl_seconds: Optional[int] = Field(
        None, description="Time to live in seconds, None for no expiration"
    )

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False

        age_seconds = (datetime.utcnow() - self.timestamp).total_seconds()
        return age_seconds > self.ttl_seconds


class ModelQueryCacheMetrics(BaseModel):
    """Metrics for query cache performance monitoring."""

    total_entries: int = Field(0, description="Total number of cache entries")
    hit_count: int = Field(0, description="Number of cache hits")
    miss_count: int = Field(0, description="Number of cache misses")
    eviction_count: int = Field(0, description="Number of entries evicted")
    total_size_bytes: int = Field(0, description="Total size of cached data in bytes")

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        total_requests = self.hit_count + self.miss_count
        if total_requests == 0:
            return 0.0
        return (self.hit_count / total_requests) * 100
