"""Vector handler metadata model.

This module provides the ModelVectorHandlerMetadata class for describing
the capabilities and configuration of a vector store handler.

Thread Safety:
    ModelVectorHandlerMetadata instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_vector_distance_metric import (
    EnumVectorDistanceMetric,
)


class ModelVectorHandlerMetadata(BaseModel):
    """Metadata describing a vector store handler.

    This model represents the capabilities and configuration of a
    vector store handler implementation (e.g., Qdrant, Pinecone, Milvus).

    Attributes:
        handler_type: The type of vector store backend (e.g., "qdrant", "pinecone").
        capabilities: List of supported capabilities (e.g., "batch_store", "filter").
        supported_metrics: List of supported distance metrics.

    Example:
        Qdrant handler::

            from omnibase_core.models.vector import (
                ModelVectorHandlerMetadata,
                EnumVectorDistanceMetric,
            )

            metadata = ModelVectorHandlerMetadata(
                handler_type="qdrant",
                capabilities=[
                    "store",
                    "batch_store",
                    "search",
                    "filter",
                    "delete",
                    "upsert",
                ],
                supported_metrics=[
                    EnumVectorDistanceMetric.COSINE,
                    EnumVectorDistanceMetric.EUCLIDEAN,
                    EnumVectorDistanceMetric.DOT_PRODUCT,
                ],
            )

        Minimal handler::

            metadata = ModelVectorHandlerMetadata(
                handler_type="simple",
                capabilities=["store", "search"],
                supported_metrics=[EnumVectorDistanceMetric.COSINE],
            )
    """

    handler_type: str = Field(
        ...,
        min_length=1,
        description="The type of vector store backend",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of supported capabilities",
    )
    supported_metrics: list[EnumVectorDistanceMetric] = Field(
        default_factory=list,
        description="List of supported distance metrics",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorHandlerMetadata"]
