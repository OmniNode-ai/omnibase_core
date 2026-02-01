"""Vector index configuration model.

This module provides the ModelVectorIndexConfig class for defining
the configuration of a vector index including dimension, metric, and
optional performance tuning parameters.

Thread Safety:
    ModelVectorIndexConfig instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_vector_distance_metric import (
    EnumVectorDistanceMetric,
)
from omnibase_core.models.vector.model_hnsw_config import ModelHnswConfig
from omnibase_core.models.vector.model_quantization_config import (
    ModelQuantizationConfig,
)


class ModelVectorIndexConfig(BaseModel):
    """Configuration for a vector index.

    This model defines the configuration parameters for creating or
    managing a vector index in a vector store.

    Attributes:
        dimension: The dimensionality of vectors in this index.
        metric: The distance metric to use for similarity calculations.
        shards: Number of shards for distributed storage (1 for single-node).
        replicas: Number of replicas for fault tolerance.
        quantization: Optional quantization configuration for memory optimization.
        hnsw_config: Optional HNSW index configuration for tuning.

    Example:
        Basic configuration::

            from omnibase_core.models.vector import (
                ModelVectorIndexConfig,
                EnumVectorDistanceMetric,
            )

            config = ModelVectorIndexConfig(
                dimension=1536,
                metric=EnumVectorDistanceMetric.COSINE,
            )

        With HNSW tuning::

            config = ModelVectorIndexConfig(
                dimension=768,
                metric=EnumVectorDistanceMetric.DOT_PRODUCT,
                shards=3,
                replicas=2,
                hnsw_config=ModelHnswConfig(m=32, ef_construction=400),
            )
    """

    dimension: int = Field(
        ...,
        ge=1,
        le=65536,
        description="Dimensionality of vectors (1-65536)",
    )
    metric: EnumVectorDistanceMetric = Field(
        default=EnumVectorDistanceMetric.COSINE,
        description="Distance metric for similarity calculations",
    )
    shards: int = Field(
        default=1,
        ge=1,
        le=128,
        description="Number of shards for distributed storage",
    )
    replicas: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Number of replicas for fault tolerance",
    )
    quantization: ModelQuantizationConfig | None = Field(
        default=None,
        description="Optional quantization configuration",
    )
    hnsw_config: ModelHnswConfig | None = Field(
        default=None,
        description="Optional HNSW index configuration",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorIndexConfig"]
