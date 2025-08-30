"""
Vector search response model for Qdrant vector database operations.

This model represents the complete response from vector similarity search,
following ONEX canonical patterns with proper typing.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.model.ai.qdrant.model_vector_search_query import (
        ModelVectorSearchQuery,
    )
    from omnibase_core.model.ai.qdrant.model_vector_search_result import (
        ModelVectorSearchResult,
    )


class ModelVectorSearchResponse(BaseModel):
    """Model representing the complete vector search response."""

    results: list["ModelVectorSearchResult"] = Field(
        ...,
        description="List of search results",
    )
    query_time_ms: float = Field(
        ...,
        description="Query execution time in milliseconds",
    )
    total_count: int = Field(..., description="Total number of matching vectors")
    collection_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Collection metadata",
    )
    search_query: "ModelVectorSearchQuery" = Field(
        ...,
        description="Original search query",
    )
