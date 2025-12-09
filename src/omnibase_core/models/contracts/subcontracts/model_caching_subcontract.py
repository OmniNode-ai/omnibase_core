"""
Caching Subcontract Model.



Dedicated subcontract model for caching functionality providing:
- Cache strategy and policy definitions
- Cache key generation and invalidation rules
- Cache performance and size management
- Distributed caching and synchronization
- Cache monitoring and metrics

This model is composed into node contracts that require caching functionality,
providing clean separation between node logic and caching behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import individual cache model components
from .model_cache_distribution import ModelCacheDistribution
from .model_cache_invalidation import ModelCacheInvalidation
from .model_cache_key_strategy import ModelCacheKeyStrategy
from .model_cache_performance import ModelCachePerformance


class ModelCachingSubcontract(BaseModel):
    """
    Caching subcontract model for cache functionality.

    Comprehensive caching subcontract providing cache strategies,
    key generation, invalidation policies, and performance tuning.
    Designed for composition into node contracts requiring caching functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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
            version=ModelSemVer(major=1, minor=0, patch=0),
            key_generation_method="composite_hash",
        ),
        description="Cache key generation strategy",
    )

    # Cache invalidation and expiration
    invalidation_policy: ModelCacheInvalidation = Field(
        default_factory=lambda: ModelCacheInvalidation(
            version=ModelSemVer(major=1, minor=0, patch=0),
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
        default_factory=lambda: ModelCachePerformance(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
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

    @model_validator(mode="after")
    def validate_memory_allocation(self) -> "ModelCachingSubcontract":
        """Validate memory allocation is reasonable."""
        if self.max_memory_mb > 16384:  # 16GB
            msg = "max_memory_mb cannot exceed 16GB for safety"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_hit_ratio(self) -> "ModelCachingSubcontract":
        """Validate hit ratio threshold is reasonable."""
        if self.hit_ratio_threshold < 0.1:
            msg = "hit_ratio_threshold should be at least 0.1 (10%)"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_cache_hierarchy(self) -> "ModelCachingSubcontract":
        """Validate L2 cache is larger than L1 when multi-level is enabled."""
        if self.multi_level_enabled:
            if self.l2_cache_size <= self.l1_cache_size:
                msg = "l2_cache_size must be larger than l1_cache_size"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
