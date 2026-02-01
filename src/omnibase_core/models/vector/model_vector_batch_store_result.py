"""Vector batch store result model.

This module provides the ModelVectorBatchStoreResult class for representing
the result of a batch embedding store operation.

Thread Safety:
    ModelVectorBatchStoreResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelVectorBatchStoreResult(BaseModel):
    """Result of a batch embedding store operation.

    This model represents the outcome of storing multiple embeddings
    in a single batch operation to a vector database.

    Attributes:
        success: Whether the overall batch operation succeeded.
            True only if all embeddings were stored successfully.
        total_stored: Number of embeddings successfully stored.
        failed_ids: List of embedding IDs that failed to store.
        execution_time_ms: Total execution time in milliseconds.

    Example:
        Fully successful batch::

            from omnibase_core.models.vector import ModelVectorBatchStoreResult

            result = ModelVectorBatchStoreResult(
                success=True,
                total_stored=100,
                failed_ids=[],
                execution_time_ms=250,
            )

        Partial failure::

            result = ModelVectorBatchStoreResult(
                success=False,
                total_stored=95,
                failed_ids=["doc_5", "doc_23", "doc_67", "doc_89", "doc_100"],
                execution_time_ms=500,
            )
    """

    success: bool = Field(
        ...,
        description="Whether all embeddings were stored successfully",
    )
    total_stored: int = Field(
        ...,
        ge=0,
        description="Number of embeddings successfully stored",
    )
    failed_ids: list[str] = Field(
        default_factory=list,
        description="List of embedding IDs that failed to store",
    )
    execution_time_ms: int = Field(
        ...,
        ge=0,
        description="Total execution time in milliseconds",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorBatchStoreResult"]
