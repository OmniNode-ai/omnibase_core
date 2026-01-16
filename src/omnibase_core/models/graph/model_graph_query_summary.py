"""Graph query summary model.

This module provides the ModelGraphQuerySummary class for query execution summary.

Thread Safety:
    ModelGraphQuerySummary instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphQuerySummary(BaseModel):
    """Summary information for a graph query execution."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    query_type: str = Field(
        default="unknown",
        description="Type of query executed (e.g., 'read', 'write', 'schema')",
    )
    database: str | None = Field(
        default=None,
        description="Name of the database the query was executed against",
    )
    contains_updates: bool = Field(
        default=False,
        description="Whether the query modified the database",
    )


__all__ = ["ModelGraphQuerySummary"]
