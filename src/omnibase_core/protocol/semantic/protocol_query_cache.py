"""
Protocol interface for query caching systems.

Defines the contract for multi-tier caching systems that optimize
semantic search performance through intelligent caching strategies.
"""

from typing import Protocol

from omnibase_core.model.semantic.model_cache_input_state import ModelCacheInputState
from omnibase_core.model.semantic.model_cache_output_state import ModelCacheOutputState


class ProtocolQueryCache(Protocol):
    """
    Protocol for query caching tools.

    This protocol defines the interface for tools that provide multi-tier
    caching capabilities for queries, embeddings, and search results.
    """

    def get_cached_results(
        self,
        input_state: ModelCacheInputState,
    ) -> ModelCacheOutputState:
        """
        Retrieve cached results for a query.

        Args:
            input_state: Input state containing cache key and retrieval parameters

        Returns:
            Output state with cached results or cache miss indication
        """
        ...

    def cache_results(self, input_state: ModelCacheInputState) -> ModelCacheOutputState:
        """
        Store results in cache.

        Args:
            input_state: Input state containing results to cache and metadata

        Returns:
            Output state with cache operation status
        """
        ...
