"""
Output state model for query cache operations.

Defines the output results and metadata from multi-tier caching
operations including cache hits, misses, and performance statistics.
"""

from typing import Dict, List, Optional

from pydantic import ConfigDict, Field

from omnibase_core.model.core.model_onex_output_state import OnexOutputState
from omnibase_core.model.semantic.model_cache_operation_statistics import \
    ModelCacheOperationStatistics
from omnibase_core.model.semantic.model_cache_result import ModelCacheResult


class ModelCacheOutputState(OnexOutputState):
    """
    Output state for query cache operations.

    Contains cached data, cache statistics, and operation metadata
    from multi-tier caching operations.
    """

    cache_hit: bool = Field(description="Whether the operation resulted in a cache hit")

    cache_level: Optional[str] = Field(
        default=None,
        description="Cache level where hit/miss occurred: memory, postgres",
    )

    cached_results: Optional[List[ModelCacheResult]] = Field(
        default=None, description="Retrieved cached results"
    )

    cached_embedding: Optional[List[float]] = Field(
        default=None, description="Retrieved cached embedding vector"
    )

    cache_statistics: ModelCacheOperationStatistics = Field(
        description="Cache performance statistics",
        default_factory=ModelCacheOperationStatistics,
    )

    operation_time_ms: Optional[int] = Field(
        default=None, description="Cache operation time in milliseconds"
    )

    cache_size_info: Optional[Dict[str, int]] = Field(
        default=None, description="Information about cache sizes and utilization"
    )

    expiry_time: Optional[str] = Field(
        default=None, description="When the cached entry will expire (ISO timestamp)"
    )

    compression_used: bool = Field(
        default=False, description="Whether compression was used for this entry"
    )

    operation_success: bool = Field(
        default=True, description="Whether the cache operation completed successfully"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
