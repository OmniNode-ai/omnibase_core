"""
Typed metadata model for reducer input.

This module provides strongly-typed metadata for reducer patterns.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelReducerMetadata(BaseModel):
    """
    Typed metadata for reducer input.

    Replaces dict[str, Any] metadata field in ModelReducerInput
    with explicit typed fields for reducer metadata.

    Note: All fields are optional as metadata may be partially populated
    depending on the source and context. This is intentional for metadata
    models that aggregate information from multiple sources.
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(extra="forbid", from_attributes=True)

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
