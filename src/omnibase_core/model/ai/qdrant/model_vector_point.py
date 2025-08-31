"""
Vector point model for Qdrant vector database operations.

This model represents a vector point with embeddings and metadata,
following ONEX canonical patterns with proper validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelVectorPoint(BaseModel):
    """Model representing a vector point for Qdrant operations."""

    point_id: str | int = Field(
        ...,
        description="Unique identifier for the vector point",
    )
    vector: list[float] = Field(..., description="Vector embedding values")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata payload for the vector",
    )

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v):
        if not v:
            msg = "Vector cannot be empty"
            raise ValueError(msg)
        if not all(isinstance(x, int | float) for x in v):
            msg = "Vector must contain only numeric values"
            raise ValueError(msg)
        return v
