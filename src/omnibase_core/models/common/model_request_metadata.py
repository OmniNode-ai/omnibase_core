"""
Typed metadata model for discovery/effect/reducer requests.

This module provides strongly-typed metadata for request patterns.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumEventPriority


class ModelRequestMetadata(BaseModel):
    """
    Typed metadata for discovery/effect/reducer requests.

    Replaces dict[str, Any] metadata field in request models
    with explicit typed fields for common request metadata.

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
        description="Source identifier of the request",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing identifier",
    )
    span_id: str | None = Field(
        default=None,
        description="Span identifier for tracing",
    )
    user_agent: str | None = Field(
        default=None,
        description="User agent making the request",
    )
    ip_address: str | None = Field(
        default=None,
        description="Client IP address",
    )
    environment: str | None = Field(
        default=None,
        description="Deployment environment (dev, staging, prod)",
    )
    priority: EnumEventPriority | None = Field(
        default=None,
        description="Request priority level (critical, high, normal, low, deferred)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for request categorization",
    )


__all__ = ["ModelRequestMetadata"]
