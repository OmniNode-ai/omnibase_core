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
    #
    # extra="allow" permits arbitrary context data (e.g., user_id, request_id)
    # to be passed through metadata while still providing typed fields for
    # common metadata patterns (trace_id, correlation_id, etc.).
    model_config = ConfigDict(extra="allow", from_attributes=True)

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
    trigger: str | None = Field(
        default=None,
        description=(
            "Event or condition that triggered this reduction operation. "
            "Used in FSM-based reducers to specify which event caused a state transition. "
            "Maps to the 'trigger' field in ModelFSMStateTransition for deterministic "
            "state machine processing."
        ),
    )


__all__ = ["ModelReducerMetadata"]
