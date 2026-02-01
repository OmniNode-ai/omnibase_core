"""Embedding model for vector store operations.

This module provides the ModelEmbedding class for representing a single
embedding vector with associated metadata.

Thread Safety:
    ModelEmbedding instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelEmbedding(BaseModel):
    """A single embedding vector with associated metadata.

    This model represents an embedding that can be stored in a vector database.
    Each embedding has a unique identifier, a vector of floats, optional metadata,
    and an optional namespace for multi-tenant scenarios.

    Attributes:
        id: Unique identifier for the embedding (e.g., document ID).
        vector: The embedding vector as a list of floats.
        metadata: Optional key-value metadata associated with the embedding.
            Uses ModelSchemaValue for type-safe value storage.
        namespace: Optional namespace for multi-tenant vector store organization.

    Example:
        Basic embedding::

            from omnibase_core.models.vector import ModelEmbedding

            embedding = ModelEmbedding(
                id="doc_123",
                vector=[0.1, 0.2, 0.3, 0.4],
            )

        With metadata and namespace::

            from omnibase_core.models.common import ModelSchemaValue

            embedding = ModelEmbedding(
                id="doc_456",
                vector=[0.5, 0.6, 0.7, 0.8],
                metadata={
                    "source": ModelSchemaValue.from_value("wikipedia"),
                    "category": ModelSchemaValue.from_value("science"),
                },
                namespace="production",
            )
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the embedding",
    )
    vector: list[float] = Field(
        ...,
        min_length=1,
        description="The embedding vector as a list of floats",
    )
    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Optional key-value metadata for the embedding",
    )
    namespace: str | None = Field(
        default=None,
        description="Optional namespace for multi-tenant organization",
    )

    @field_validator("vector")
    @classmethod
    def validate_no_nan_or_inf(cls, v: list[float]) -> list[float]:
        """Validate that vector contains no NaN or Inf values.

        Embedding vectors must contain only finite numeric values. NaN or Inf
        values indicate corrupted data or computational errors and would cause
        undefined behavior in similarity calculations.

        Args:
            v: The embedding vector to validate.

        Returns:
            The validated vector if all values are finite.

        Raises:
            ValueError: If any value in the vector is NaN or Inf.
        """
        for i, value in enumerate(v):
            if math.isnan(value):
                raise ValueError(
                    f"Embedding vector contains NaN at index {i}. "
                    "All values must be finite numbers."
                )
            if math.isinf(value):
                raise ValueError(
                    f"Embedding vector contains Inf at index {i}. "
                    "All values must be finite numbers."
                )
        return v

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelEmbedding"]
