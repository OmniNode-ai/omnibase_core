"""
Typed metadata model for discovery/effect/reducer requests.

This module provides strongly-typed metadata for request patterns.
"""

from pydantic import BaseModel, Field


class ModelRequestMetadata(BaseModel):
    """
    Typed metadata for discovery/effect/reducer requests.

    Replaces dict[str, Any] metadata field in request models
    with explicit typed fields for common request metadata.
    """

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
    environment: str | None = Field(
        default=None,
        description="Deployment environment (dev, staging, prod)",
    )
    priority: str | None = Field(
        default=None,
        description="Request priority level",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for request categorization",
    )


__all__ = ["ModelRequestMetadata"]
