"""
Vector search query model for Qdrant vector database operations.

This model defines parameters for vector similarity search queries,
following ONEX canonical patterns with proper validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelVectorSearchQuery(BaseModel):
    """Model representing a vector similarity search query."""

    query_vector: list[float] = Field(
        ...,
        description="Query vector for similarity search",
    )
    collection_name: str = Field(..., description="Name of the collection to search")
    limit: int = Field(default=10, description="Maximum number of results to return")
    score_threshold: float | None = Field(
        None,
        description="Minimum similarity score threshold",
    )
    filter_conditions: dict[str, Any] | None = Field(
        None,
        description="Metadata filter conditions",
    )
    with_payload: bool = Field(
        default=True,
        description="Include payload in search results",
    )
    with_vectors: bool = Field(
        default=False,
        description="Include vectors in search results",
    )

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v <= 0 or v > 10000:
            msg = "Limit must be between 1 and 10000"
            raise ValueError(msg)
        return v

    @field_validator("score_threshold")
    @classmethod
    def validate_score_threshold(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "Score threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v
