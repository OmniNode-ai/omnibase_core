"""
Typed metadata model for reducer input.

This module provides strongly-typed metadata for reducer patterns.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelReducerMetadata(BaseModel):
    """
    Typed metadata for reducer input.

    Replaces dict[str, Any] metadata field in ModelReducerInput
    with explicit typed fields for reducer metadata.
    """

    source: str | None = Field(
        default=None,
        description="Source identifier",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing identifier",
    )
    span_id: str | None = Field(
        default=None,
        description="Span identifier for tracing",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracking",
    )
    group_key: str | None = Field(
        default=None,
        description="Key for grouping operations",
    )
    partition_id: UUID | None = Field(
        default=None,
        description="Partition identifier for distributed processing",
    )
    window_id: UUID | None = Field(
        default=None,
        description="Window identifier for streaming operations",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )


__all__ = ["ModelReducerMetadata"]
