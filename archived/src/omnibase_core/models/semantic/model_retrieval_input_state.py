"""
Input state model for hybrid retrieval operations.

Defines the input parameters for hybrid retrieval systems that combine
multiple search strategies such as BM25 and dense vector search.
"""

from pydantic import ConfigDict, Field

from omnibase_core.models.core.model_onex_base_state import (
    ModelOnexInputState as OnexInputState,
)
from omnibase_core.models.semantic.model_retrieval_filters import ModelRetrievalFilters


class ModelRetrievalInputState(OnexInputState):
    """
    Input state for hybrid retrieval operations.

    Contains search query, filters, and retrieval parameters
    required for hybrid search operations.
    """

    query: str = Field(description="Search query string", min_length=1)

    filters: ModelRetrievalFilters | None = Field(
        default=None,
        description="Optional metadata filters for search",
    )

    top_k: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Number of results to return",
    )

    retrieval_strategy: str = Field(
        default="hybrid",
        description="Retrieval strategy: bm25, dense, hybrid",
    )

    bm25_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weight for BM25 scores in hybrid mode",
    )

    dense_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weight for dense vector scores in hybrid mode",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
