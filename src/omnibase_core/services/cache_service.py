"""
In-memory cache service implementation.

Provides a thread-safe, TTL-aware cache service that implements ProtocolCacheService
without external dependencies. Suitable for development and testing environments.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from omnibase.protocols.core import ProtocolCacheService, ProtocolCacheServiceProvider
from omnibase.protocols.types.core_types import ContextValue, ProtocolCacheStatistics


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    data: dict[str, Any]
    created_at: float
    expires_at: float | None = None
    access_count: int = 0
    last_accessed: float = 0


class InMemoryCacheService(ProtocolCacheService[dict[str, Any]]):
    """
    Thread-safe in-memory cache service with TTL support.

    Implements ProtocolCacheService for dependency injection via ModelONEXContainer.
    Provides proper cache semantics without external dependencies.
    """

    def __init__(self, default_ttl_seconds: int = 300, max_entries: int = 10000):
        """
        Initialize in-memory cache.

        Args:
            default_ttl_seconds: Default time-to-live for cache entries
            max_entries: Maximum number of cache entries before eviction
        """
        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries

        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached data by key with TTL checking."""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            current_time = time.time()

            # Check if entry has expired
            if entry.expires_at and current_time > entry.expires_at:
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            # Update access tracking
            entry.access_count += 1
            entry.last_accessed = current_time
            self._stats["hits"] += 1

            return entry.data.copy()  # Return copy to prevent external mutations

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        """Store data in cache with TTL."""
        async with self._lock:
            current_time = time.time()
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

            # Calculate expiration time
            expires_at = current_time + ttl if ttl > 0 else None

            # Create cache entry
            entry = CacheEntry(
                data=value.copy(),  # Store copy to prevent external mutations
                created_at=current_time,
                expires_at=expires_at,
                access_count=0,
                last_accessed=current_time,
            )

            # Check if we need to evict entries
            if len(self._cache) >= self.max_entries and key not in self._cache:
                await self._evict_entries()

            self._cache[key] = entry
            self._stats["sets"] += 1

            return True

    async def delete(self, key: str) -> bool:
        """Delete cached data by key."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                return True
            return False

    async def clear(self, pattern: str | None = None) -> int:
        """Clear cache entries, optionally by pattern."""
        async with self._lock:
            if pattern is None:
                # Clear all entries
                cleared_count = len(self._cache)
                self._cache.clear()
                return cleared_count

            # Clear entries matching pattern
            keys_to_delete = [key for key in self._cache.keys() if pattern in key]

            for key in keys_to_delete:
                del self._cache[key]

            return len(keys_to_delete)

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        result = await self.get(key)
        return result is not None

    def get_stats(self) -> ProtocolCacheStatistics:
        """Get cache statistics."""
        current_time = time.time()

        # Count non-expired entries
        valid_entries = 0
        expired_entries = 0

        for entry in self._cache.values():
            if entry.expires_at and current_time > entry.expires_at:
                expired_entries += 1
            else:
                valid_entries += 1

        # Create a simple implementation of ProtocolCacheStatistics
        from dataclasses import dataclass

        @dataclass
        class CacheStats:
            hit_count: int
            miss_count: int
            total_requests: int
            hit_ratio: float
            memory_usage_bytes: int
            entry_count: int
            eviction_count: int
            last_accessed: datetime | None
            cache_size_limit: int | None

        return CacheStats(
            hit_count=self._stats["hits"],
            miss_count=self._stats["misses"],
            total_requests=self._stats["hits"] + self._stats["misses"],
            hit_ratio=self._stats["hits"]
            / max(1, self._stats["hits"] + self._stats["misses"]),
            memory_usage_bytes=0,  # Would need actual memory measurement
            entry_count=len(self._cache),
            eviction_count=self._stats["evictions"],
            last_accessed=(
                datetime.fromtimestamp(
                    max(
                        (entry.last_accessed for entry in self._cache.values()),
                        default=0,
                    ),
                )
                if self._cache
                else None
            ),
            cache_size_limit=self.max_entries,
        )

    async def _evict_entries(self, evict_count: int = None) -> None:
        """Evict entries using LRU policy."""
        if evict_count is None:
            evict_count = max(1, len(self._cache) // 10)  # Evict 10%

        # Sort by last_accessed time (LRU)
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].last_accessed)

        evicted = 0
        for key, entry in sorted_entries:
            if evicted >= evict_count:
                break

            del self._cache[key]
            evicted += 1

        self._stats["evictions"] += evicted


class InMemoryCacheServiceProvider(ProtocolCacheServiceProvider[dict[str, Any]]):
    """Provider for in-memory cache service."""

    def __init__(self, default_ttl_seconds: int = 300, max_entries: int = 10000):
        """Initialize provider with configuration."""
        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries
        self._cache_service: InMemoryCacheService | None = None

    def create_cache_service(self) -> ProtocolCacheService[dict[str, Any]]:
        """Create or return existing cache service instance."""
        if self._cache_service is None:
            self._cache_service = InMemoryCacheService(
                default_ttl_seconds=self.default_ttl_seconds,
                max_entries=self.max_entries,
            )
        return self._cache_service

    def get_cache_configuration(self) -> dict[str, ContextValue]:
        """Get cache configuration parameters."""
        return {
            "type": "in_memory",
            "default_ttl_seconds": self.default_ttl_seconds,
            "max_entries": self.max_entries,
            "thread_safe": True,
            "persistent": False,
        }
