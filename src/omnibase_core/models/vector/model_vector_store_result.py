"""Vector store result model.

This module provides the ModelVectorStoreResult class for representing
the result of a single embedding store operation.

Thread Safety:
    ModelVectorStoreResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelVectorStoreResult(BaseModel):
    """Result of a single embedding store operation.

    This model represents the outcome of storing a single embedding
    in a vector database.

    Attributes:
        success: Whether the store operation succeeded.
        embedding_id: The ID of the stored embedding.
        index_name: The name of the index where the embedding was stored.
        timestamp: Timestamp when the operation completed.

    Example:
        Successful store::

            from datetime import datetime, UTC
            from omnibase_core.models.vector import ModelVectorStoreResult

            result = ModelVectorStoreResult(
                success=True,
                embedding_id="doc_123",
                index_name="documents",
                timestamp=datetime.now(UTC),
            )

        Failed store::

            result = ModelVectorStoreResult(
                success=False,
                embedding_id="doc_456",
                index_name="documents",
            )
    """

    success: bool = Field(
        ...,
        description="Whether the store operation succeeded",
    )
    # ONEX_EXCLUDE: string_id - External vector store ID (Qdrant, Pinecone, etc.)
    embedding_id: str = Field(
        ...,
        min_length=1,
        description="The ID of the embedding",
    )
    index_name: str = Field(
        ...,
        min_length=1,
        description="The index where the embedding was stored",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="Timestamp when the operation completed",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorStoreResult"]
