"""Vector delete result model.

This module provides the ModelVectorDeleteResult class for representing
the result of a vector deletion operation.

Thread Safety:
    ModelVectorDeleteResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelVectorDeleteResult(BaseModel):
    """Result of a vector deletion operation.

    This model represents the outcome of deleting an embedding
    from a vector database.

    Attributes:
        success: Whether the delete operation succeeded.
        embedding_id: The ID of the embedding that was deleted.
        deleted: Whether the embedding was actually deleted
            (False if it didn't exist).

    Example:
        Successful deletion::

            from omnibase_core.models.vector import ModelVectorDeleteResult

            result = ModelVectorDeleteResult(
                success=True,
                embedding_id="doc_123",
                deleted=True,
            )

        Embedding not found::

            result = ModelVectorDeleteResult(
                success=True,
                embedding_id="doc_456",
                deleted=False,  # Didn't exist
            )

        Failed deletion::

            result = ModelVectorDeleteResult(
                success=False,
                embedding_id="doc_789",
                deleted=False,
            )
    """

    success: bool = Field(
        ...,
        description="Whether the delete operation succeeded",
    )
    # ONEX_EXCLUDE: string_id - External vector store ID (Qdrant, Pinecone, etc.)
    embedding_id: str = Field(
        ...,
        min_length=1,
        description="The ID of the embedding",
    )
    deleted: bool = Field(
        ...,
        description="Whether the embedding was actually deleted",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorDeleteResult"]
