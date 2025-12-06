"""
Computation Cache - Caching layer for expensive computations.

Provides TTL-based caching with LRU eviction and memory management.
"""

from datetime import UTC, datetime, timedelta
from typing import Any


class ComputationCache:
    """
    Caching layer for expensive computations with TTL and memory management.
    """

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        self.max_size = max_size
        self.default_ttl_minutes = default_ttl_minutes
        self._cache: dict[
            str,
            tuple[Any, datetime, int],
        ] = {}  # key -> (value, expiry, access_count)

    def get(self, cache_key: str) -> Any | None:
        """Get cached value if valid and not expired."""
        if cache_key not in self._cache:
            return None

        value, expiry, access_count = self._cache[cache_key]

        # Check expiry (use UTC for consistent timezone-aware comparison)
        if datetime.now(UTC) > expiry:
            del self._cache[cache_key]
            return None

        # Update access count
        self._cache[cache_key] = (value, expiry, access_count + 1)
        return value

    def put(
        self,
        cache_key: str,
        value: Any,
        ttl_minutes: int | None = None,
    ) -> None:
        """Cache value with TTL."""
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        ttl = ttl_minutes or self.default_ttl_minutes
        # Use UTC for consistent timezone-aware expiry times
        expiry = datetime.now(UTC) + timedelta(minutes=ttl)
        self._cache[cache_key] = (value, expiry, 1)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._cache:
            return

        # Find item with lowest access count (simple LRU approximation)
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        del self._cache[lru_key]

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        now = datetime.now(UTC)
        expired_count = sum(1 for _, expiry, _ in self._cache.values() if expiry <= now)

        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "valid_entries": len(self._cache) - expired_count,
            "max_size": self.max_size,
        }
