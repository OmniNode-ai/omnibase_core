"""
Input state model for query cache operations.

Defines the input parameters for multi-tier caching operations
including cache retrieval, storage, and management operations.
"""

from typing import List, Optional

from pydantic import ConfigDict, Field

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState
from omnibase_core.model.semantic.model_cache_result import ModelCacheResult
from omnibase_core.model.semantic.model_retrieval_filters import \
    ModelRetrievalFilters


class ModelCacheInputState(ModelOnexInputState):
    """
    Input state for query cache operations.

    Contains cache keys, data to cache, and operation parameters
    required for multi-tier caching operations.
    """

    operation_type: str = Field(description="Cache operation: get, set, delete, stats")

    cache_key: Optional[str] = Field(
        default=None, description="Cache key for retrieval operations"
    )

    query_text: Optional[str] = Field(
        default=None, description="Original query text for cache key generation"
    )

    filters: Optional[ModelRetrievalFilters] = Field(
        default=None, description="Search filters for cache key generation"
    )

    retriever_type: Optional[str] = Field(
        default=None, description="Type of retriever used for search"
    )

    results_to_cache: Optional[List[ModelCacheResult]] = Field(
        default=None, description="Results to store in cache"
    )

    embedding_text: Optional[str] = Field(
        default=None, description="Text content for embedding caching"
    )

    embedding_vector: Optional[List[float]] = Field(
        default=None, description="Embedding vector to cache"
    )

    model_name: Optional[str] = Field(
        default=None, description="Name of the embedding model"
    )

    ttl_override: Optional[int] = Field(
        default=None, ge=1, description="Override TTL for this cache entry in seconds"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
