"""
Model for contract service internal state.

This model represents the internal state of the contract service
including cache management and performance metrics.
"""

from pydantic import BaseModel, Field

from .model_contract_cache_entry import ModelContractCacheEntry


class ModelContractServiceState(BaseModel):
    """Represents internal state of contract service."""

    cache_enabled: bool = Field(True, description="Whether caching is enabled")
    cache_max_size: int = Field(100, description="Maximum cache entries")
    cache_entries: dict[str, ModelContractCacheEntry] = Field(
        default_factory=dict,
        description="Cached contract entries",
    )
    total_loads: int = Field(default=0, description="Total contracts loaded")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    total_validations: int = Field(default=0, description="Total validations performed")
    validation_failures: int = Field(
        default=0,
        description="Number of validation failures",
    )

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def cache_size(self) -> int:
        """Get current cache size."""
        return len(self.cache_entries)

    @property
    def validation_success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_validations == 0:
            return 1.0
        return (
            self.total_validations - self.validation_failures
        ) / self.total_validations

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses += 1

    def record_load(self) -> None:
        """Record a contract load."""
        self.total_loads += 1

    def record_validation(self, success: bool) -> None:
        """
        Record a validation attempt.

        Args:
            success: Whether validation succeeded
        """
        self.total_validations += 1
        if not success:
            self.validation_failures += 1

    def clear_cache(self) -> int:
        """
        Clear all cache entries.

        Returns:
            int: Number of entries cleared
        """
        cleared_count = len(self.cache_entries)
        self.cache_entries.clear()
        return cleared_count

    def evict_oldest_entries(self, keep_count: int) -> int:
        """
        Evict oldest cache entries to maintain size limit.

        Args:
            keep_count: Number of entries to keep

        Returns:
            int: Number of entries evicted
        """
        if len(self.cache_entries) <= keep_count:
            return 0

        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self.cache_entries.items(),
            key=lambda x: x[1].last_accessed,
        )

        # Keep only the most recent entries
        entries_to_keep = dict(sorted_entries[-keep_count:])
        evicted_count = len(self.cache_entries) - len(entries_to_keep)

        self.cache_entries = entries_to_keep
        return evicted_count
