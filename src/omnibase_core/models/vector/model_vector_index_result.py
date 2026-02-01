"""Vector index operation result model.

This module provides the ModelVectorIndexResult class for representing
the result of an index creation or management operation.

Thread Safety:
    ModelVectorIndexResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_vector_distance_metric import (
    EnumVectorDistanceMetric,
)


class ModelVectorIndexResult(BaseModel):
    """Result of a vector index operation.

    This model represents the outcome of creating, updating, or
    querying metadata about a vector index.

    Attributes:
        success: Whether the index operation succeeded.
        index_name: The name of the index.
        dimension: The dimensionality of vectors in the index.
        metric: The distance metric used by the index.
        created_at: Timestamp when the index was created.

    Example:
        Index created::

            from datetime import datetime, UTC
            from omnibase_core.models.vector import (
                ModelVectorIndexResult,
                EnumVectorDistanceMetric,
            )

            result = ModelVectorIndexResult(
                success=True,
                index_name="documents",
                dimension=1536,
                metric=EnumVectorDistanceMetric.COSINE,
                created_at=datetime.now(UTC),
            )

        Index creation failed::

            result = ModelVectorIndexResult(
                success=False,
                index_name="documents",
                dimension=1536,
                metric=EnumVectorDistanceMetric.COSINE,
            )
    """

    success: bool = Field(
        ...,
        description="Whether the index operation succeeded",
    )
    index_name: str = Field(
        ...,
        min_length=1,
        description="The name of the index",
    )
    dimension: int = Field(
        ...,
        ge=1,
        description="Dimensionality of vectors in the index",
    )
    metric: EnumVectorDistanceMetric = Field(
        ...,
        description="Distance metric used by the index",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the index was created",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorIndexResult"]
