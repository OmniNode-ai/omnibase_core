#!/usr/bin/env python3
"""
Caching Subcontract Model - ONEX Standards Compliant.

Dedicated subcontract model for caching functionality providing:
- Cache strategy and policy definitions
- Cache key generation and invalidation rules
- Cache performance and size management
- Distributed caching and synchronization
- Cache monitoring and metrics

This model is composed into node contracts that require caching functionality,
providing clean separation between node logic and caching behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ModelCacheKeyStrategy(BaseModel):
    """
    Cache key generation strategy.

    Defines how cache keys are generated,
    including namespacing, hashing, and versioning.
    """

    key_generation_method: str = Field(
        ...,
        description="Method for generating cache keys",
        min_length=1,
    )

    namespace: str | None = Field(
        default=None,
        description="Namespace prefix for cache keys",
    )

    include_version: bool = Field(
        default=True,
        description="Include version in cache keys",
    )

    hash_algorithm: str = Field(
        default="sha256",
        description="Hash algorithm for key generation",
    )

    key_separator: str = Field(
        default=":",
        description="Separator for cache key components",
    )

    max_key_length: int = Field(
        default=250,
        description="Maximum length for cache keys",
        ge=1,
    )


class ModelCacheInvalidation(BaseModel):
    """
    Cache invalidation policy.

    Defines cache invalidation strategies,
    triggers, and cleanup policies.
    """

    invalidation_strategy: str = Field(
        ...,
        description="Strategy for cache invalidation",
        min_length=1,
    )

    ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cache entries",
        ge=1,
    )

    max_idle_seconds: int = Field(
        default=600,
        description="Maximum idle time before invalidation",
        ge=1,
    )

    invalidation_triggers: list[str] = Field(
        default_factory=list,
        description="Events that trigger cache invalidation",
    )

    batch_invalidation: bool = Field(
        default=False,
        description="Enable batch invalidation for efficiency",
    )

    lazy_expiration: bool = Field(
        default=True,
        description="Use lazy expiration to reduce overhead",
    )


class ModelCacheDistribution(BaseModel):
    """
    Distributed caching configuration.

    Defines distributed cache behavior,
    synchronization, and consistency policies.
    """

    distributed_enabled: bool = Field(
        default=False,
        description="Enable distributed caching",
    )

    consistency_level: str = Field(
        default="eventual",
        description="Consistency level for distributed cache",
    )

    replication_factor: int = Field(
        default=2,
        description="Number of cache replicas",
        ge=1,
    )

    partition_strategy: str = Field(
        default="consistent_hash",
        description="Partitioning strategy for distribution",
    )

    sync_interval_ms: int = Field(
        default=30000,
        description="Synchronization interval",
        ge=1000,
    )

    conflict_resolution: str = Field(
        default="last_writer_wins",
        description="Conflict resolution strategy",
    )


class ModelCachePerformance(BaseModel):
    """
    Cache performance configuration.

    Defines performance tuning parameters,
    monitoring, and optimization settings.
    """

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


class ModelCachingSubcontract(BaseModel):
    """
    Caching subcontract model for cache functionality.

    Comprehensive caching subcontract providing cache strategies,
    key generation, invalidation policies, and performance tuning.
    Designed for composition into node contracts requiring caching functionality.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Core caching configuration
    caching_enabled: bool = Field(
        default=True,
        description="Enable caching functionality",
    )

    cache_strategy: str = Field(default="lru", description="Primary caching strategy")

    cache_backend: str = Field(
        default="memory",
        description="Cache backend implementation",
    )

    # Cache sizing and capacity
    max_entries: int = Field(
        default=10000,
        description="Maximum number of cache entries",
        ge=1,
    )

    max_memory_mb: int = Field(
        default=512,
        description="Maximum memory allocation in MB",
        ge=1,
    )

    entry_size_limit_kb: int = Field(
        default=1024,
        description="Maximum size per cache entry in KB",
        ge=1,
    )

    # Cache key management
    key_strategy: ModelCacheKeyStrategy = Field(
        default_factory=lambda: ModelCacheKeyStrategy(
            key_generation_method="composite_hash",
        ),
        description="Cache key generation strategy",
    )

    # Cache invalidation and expiration
    invalidation_policy: ModelCacheInvalidation = Field(
        default_factory=lambda: ModelCacheInvalidation(
            invalidation_strategy="ttl_based",
        ),
        description="Cache invalidation configuration",
    )

    # Distributed caching (optional)
    distribution_config: ModelCacheDistribution | None = Field(
        default=None,
        description="Distributed caching configuration",
    )

    # Performance tuning
    performance_config: ModelCachePerformance = Field(
        default_factory=ModelCachePerformance,
        description="Cache performance configuration",
    )

    # Cache warming and preloading
    warm_up_enabled: bool = Field(
        default=False,
        description="Enable cache warming on startup",
    )

    warm_up_sources: list[str] = Field(
        default_factory=list,
        description="Data sources for cache warming",
    )

    warm_up_batch_size: int = Field(
        default=100,
        description="Batch size for cache warming",
        ge=1,
    )

    # Cache monitoring and metrics
    metrics_enabled: bool = Field(
        default=True,
        description="Enable cache metrics collection",
    )

    detailed_metrics: bool = Field(
        default=False,
        description="Enable detailed cache metrics",
    )

    hit_ratio_threshold: float = Field(
        default=0.8,
        description="Minimum hit ratio threshold",
        ge=0.0,
        le=1.0,
    )

    performance_monitoring: bool = Field(
        default=True,
        description="Enable cache performance monitoring",
    )

    # Cache persistence (optional)
    persistence_enabled: bool = Field(
        default=False,
        description="Enable cache persistence to disk",
    )

    persistence_interval_ms: int = Field(
        default=60000,
        description="Persistence interval",
        ge=1000,
    )

    recovery_enabled: bool = Field(
        default=False,
        description="Enable cache recovery on startup",
    )

    # Cache hierarchy (multi-level caching)
    multi_level_enabled: bool = Field(
        default=False,
        description="Enable multi-level caching",
    )

    l1_cache_size: int = Field(default=1000, description="L1 cache size", ge=1)

    l2_cache_size: int = Field(default=10000, description="L2 cache size", ge=1)

    promotion_threshold: int = Field(
        default=3,
        description="Hit threshold for L2 to L1 promotion",
        ge=1,
    )

    @field_validator("max_memory_mb")
    @classmethod
    def validate_memory_allocation(cls, v: int) -> int:
        """Validate memory allocation is reasonable."""
        if v > 16384:  # 16GB
            msg = "max_memory_mb cannot exceed 16GB for safety"
            raise ValueError(msg)
        return v

    @field_validator("hit_ratio_threshold")
    @classmethod
    def validate_hit_ratio(cls, v: float) -> float:
        """Validate hit ratio threshold is reasonable."""
        if v < 0.1:
            msg = "hit_ratio_threshold should be at least 0.1 (10%)"
            raise ValueError(msg)
        return v

    @field_validator("l2_cache_size")
    @classmethod
    def validate_cache_hierarchy(cls, v: int, info: ValidationInfo) -> int:
        """Validate L2 cache is larger than L1 when multi-level is enabled."""
        if info.data and info.data.get("multi_level_enabled", False):
            l1_size = info.data.get("l1_cache_size", 1000)
            if v <= l1_size:
                msg = "l2_cache_size must be larger than l1_cache_size"
                raise ValueError(msg)
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
