"""
ModelComputeCacheConfig - Configuration for NodeCompute caching behavior.

Provides tunable cache parameters for production deployment, allowing
optimization for different workload characteristics and memory constraints.

Key Capabilities:
- Configurable cache size limits
- TTL-based expiration control
- Eviction policy selection (LRU/LFU/FIFO)
- Cache statistics tracking

Thread Safety: Cache operations must be synchronized by implementation.
Memory Usage: ~1KB per cached entry (varies by computation size).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_cache_eviction_policy import EnumCacheEvictionPolicy

__all__ = ["ModelComputeCacheConfig"]


class ModelComputeCacheConfig(BaseModel):
    """
    Configuration for computation caching in NodeCompute.

    This model provides production-tunable cache settings for optimizing
    NodeCompute performance across different workload patterns.

    Thread Safety:
        Cache operations must be synchronized by implementation.
        See docs/THREADING.md for thread-safe patterns.

    Memory Implications:
        - Small workload (<100 computations/sec): max_size=128, ~128KB
        - Medium workload (100-1000/sec): max_size=512, ~512KB
        - Large workload (>1000/sec): max_size=2048, ~2MB

    Attributes:
        max_size: Maximum number of cached computations
        ttl_seconds: Time-to-live for cached entries (None = no expiration)
        eviction_policy: Cache eviction strategy (lru/lfu/fifo)
        enable_stats: Enable cache hit/miss statistics tracking
    """

    model_config = ConfigDict(frozen=False, validate_assignment=True, extra="forbid")

    max_size: int = Field(
        default=128,
        ge=1,
        le=10000,
        description="Maximum number of cached computations. Default conservative for production.",
    )

    ttl_seconds: int | None = Field(
        default=3600,  # 1 hour
        ge=1,
        description="Time-to-live for cached entries in seconds. None = no expiration.",
    )

    eviction_policy: EnumCacheEvictionPolicy = Field(
        default=EnumCacheEvictionPolicy.LRU,
        description="Cache eviction policy: lru (least recently used), lfu (least frequently used), fifo",
    )

    enable_stats: bool = Field(
        default=True,
        description="Enable cache hit/miss statistics for monitoring",
    )

    def get_ttl_minutes(self) -> int | None:
        """
        Convert TTL from seconds to minutes.

        Returns:
            TTL in minutes, or None if no expiration
        """
        if self.ttl_seconds is None:
            return None
        return self.ttl_seconds // 60

    def get_effective_ttl_seconds(self) -> int:
        """
        Get effective TTL in seconds, with 0 indicating no expiration.

        Returns:
            TTL in seconds (0 if None/disabled)
        """
        return self.ttl_seconds if self.ttl_seconds is not None else 0

    def validate_memory_requirements(
        self, avg_entry_size_kb: float = 1.0
    ) -> dict[str, float]:
        """
        Estimate memory requirements for current configuration.

        Args:
            avg_entry_size_kb: Average size of cached entry in KB (default: 1KB)

        Returns:
            Dictionary with memory estimates:
            - estimated_memory_mb: Estimated total memory usage
            - max_memory_mb: Maximum possible memory usage
            - entries_per_mb: Cache entries per MB of memory
        """
        estimated_memory_mb = (self.max_size * avg_entry_size_kb) / 1024
        entries_per_mb = 1024 / avg_entry_size_kb

        return {
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "max_memory_mb": round(estimated_memory_mb * 1.2, 2),  # 20% overhead
            "entries_per_mb": round(entries_per_mb, 1),
        }
