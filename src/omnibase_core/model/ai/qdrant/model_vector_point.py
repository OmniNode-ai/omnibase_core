"""
Vector point model for Qdrant vector database operations.

This model represents a vector point with embeddings and metadata,
following ONEX canonical patterns with proper validation.
"""

from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field, field_validator


class ModelVectorPoint(BaseModel):
    """Model representing a vector point for Qdrant operations."""

    point_id: Union[str, int] = Field(
        ..., description="Unique identifier for the vector point"
    )
    vector: List[float] = Field(..., description="Vector embedding values")
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata payload for the vector"
    )

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v):
        if not v:
            raise ValueError("Vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numeric values")
        return v
