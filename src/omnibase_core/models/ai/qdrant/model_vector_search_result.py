"""
Vector search result model for Qdrant vector database operations.

This model represents a single search result from vector similarity search,
following ONEX canonical patterns with proper validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelVectorSearchResult(BaseModel):
    """Model representing a single vector search result."""

    point_id: str | int = Field(
        ...,
        description="ID of the matching vector point",
    )
    score: float = Field(..., description="Similarity score for the match")
    payload: dict[str, Any] | None = Field(
        None,
        description="Metadata payload of the result",
    )
    vector: list[float] | None = Field(
        None,
        description="Vector values if requested",
    )

    @field_validator("score")
    @classmethod
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v
