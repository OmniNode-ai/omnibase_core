"""Vector search result model.

This module provides the ModelVectorSearchResult class for representing
a single result from a similarity search operation.

Thread Safety:
    ModelVectorSearchResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelVectorSearchResult(BaseModel):
    """A single result from a vector similarity search.

    This model represents one matching vector from a search operation,
    including the similarity score and optional metadata/vector data.

    Attributes:
        id: Unique identifier of the matching embedding.
        score: Similarity/distance score. Interpretation depends on both the
            distance metric AND the vector store backend:

            **Cosine metric** (backend-specific):
                - Qdrant: Returns cosine distance (1 - cosine_similarity).
                  Range 0-2, where 0 = identical, 2 = opposite. Lower is better.
                - Pinecone: Returns cosine similarity directly.
                  Range -1 to 1, where 1 = identical. Higher is better.
                - Other backends may vary; consult their documentation.

            **Euclidean metric**:
                - Returns L2 distance. Range 0 to infinity.
                - Lower values indicate more similar vectors.

            **Dot product metric**:
                - Returns dot product value. Range varies by normalization.
                - Higher values indicate more similar vectors.

            **Manhattan metric**:
                - Returns L1 distance. Range 0 to infinity.
                - Lower values indicate more similar vectors.

            Always verify score interpretation with your specific backend.
        metadata: Optional metadata associated with the matching embedding.
        vector: Optional embedding vector (if requested in search).

    Example:
        Basic search result::

            from omnibase_core.models.vector import ModelVectorSearchResult

            result = ModelVectorSearchResult(
                id="doc_123",
                score=0.95,
            )

        With metadata and vector::

            from omnibase_core.models.common import ModelSchemaValue

            result = ModelVectorSearchResult(
                id="doc_456",
                score=0.87,
                metadata={
                    "title": ModelSchemaValue.from_value("Introduction to ML"),
                    "author": ModelSchemaValue.from_value("Jane Doe"),
                },
                vector=[0.1, 0.2, 0.3, 0.4],
            )
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the matching embedding",
    )
    score: float = Field(
        ...,
        description="Similarity score (interpretation depends on metric)",
    )
    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Optional metadata associated with the embedding",
    )
    vector: list[float] | None = Field(
        default=None,
        description="Optional embedding vector if requested in search",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorSearchResult"]
