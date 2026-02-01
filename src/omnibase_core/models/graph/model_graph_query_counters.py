"""Graph query counters model.

This module provides the ModelGraphQueryCounters class for tracking
database operation statistics during query execution.

Thread Safety:
    ModelGraphQueryCounters instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphQueryCounters(BaseModel):
    """Counters for graph query statistics.

    Tracks the number of database operations performed during a query.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    nodes_created: int = Field(
        default=0,
        description="Number of nodes created",
        ge=0,
    )
    nodes_deleted: int = Field(
        default=0,
        description="Number of nodes deleted",
        ge=0,
    )
    relationships_created: int = Field(
        default=0,
        description="Number of relationships created",
        ge=0,
    )
    relationships_deleted: int = Field(
        default=0,
        description="Number of relationships deleted",
        ge=0,
    )
    properties_set: int = Field(
        default=0,
        description="Number of properties set",
        ge=0,
    )
    labels_added: int = Field(
        default=0,
        description="Number of labels added",
        ge=0,
    )
    labels_removed: int = Field(
        default=0,
        description="Number of labels removed",
        ge=0,
    )


__all__ = ["ModelGraphQueryCounters"]
