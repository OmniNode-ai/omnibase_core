"""HNSW index configuration model.

This module provides the ModelHnswConfig class for HNSW index tuning.

Thread Safety:
    ModelHnswConfig instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelHnswConfig(BaseModel):
    """HNSW (Hierarchical Navigable Small World) index configuration.

    HNSW is a graph-based index structure for approximate nearest neighbor search.

    Attributes:
        m: Number of connections per element (higher = more accuracy, more memory).
        ef_construction: Size of dynamic candidate list during index construction.
        ef_search: Size of dynamic candidate list during search.

    Example:
        >>> config = ModelHnswConfig(m=16, ef_construction=200, ef_search=100)
    """

    m: int = Field(
        default=16,
        ge=4,
        le=64,
        description="Number of connections per element (4-64)",
    )
    ef_construction: int = Field(
        default=200,
        ge=10,
        le=2000,
        description="Construction-time dynamic candidate list size",
    )
    ef_search: int = Field(
        default=100,
        ge=10,
        le=2000,
        description="Search-time dynamic candidate list size",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelHnswConfig"]
