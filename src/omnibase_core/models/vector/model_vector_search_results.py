"""Vector search results container model.

This module provides the ModelVectorSearchResults class for representing
the complete results of a vector similarity search operation.

Thread Safety:
    ModelVectorSearchResults instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.vector.model_vector_search_result import (
    ModelVectorSearchResult,
)


class ModelVectorSearchResults(BaseModel):
    """Container for vector similarity search results.

    This model represents the complete results of a vector search operation,
    including all matching results and timing information.

    Attributes:
        results: List of search results sorted by relevance.
        total_results: Total number of results returned.
        query_time_ms: Time taken to execute the query in milliseconds.

    Example:
        Search results::

            from omnibase_core.models.vector import (
                ModelVectorSearchResults,
                ModelVectorSearchResult,
            )

            results = ModelVectorSearchResults(
                results=[
                    ModelVectorSearchResult(id="doc_1", score=0.95),
                    ModelVectorSearchResult(id="doc_2", score=0.87),
                    ModelVectorSearchResult(id="doc_3", score=0.82),
                ],
                total_results=3,
                query_time_ms=15,
            )

        Empty results::

            results = ModelVectorSearchResults(
                results=[],
                total_results=0,
                query_time_ms=5,
            )
    """

    results: list[ModelVectorSearchResult] = Field(
        default_factory=list,
        description="List of search results sorted by relevance",
    )
    total_results: int = Field(
        ...,
        ge=0,
        description="Total number of results returned",
    )
    query_time_ms: int = Field(
        ...,
        ge=0,
        description="Query execution time in milliseconds",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorSearchResults"]
