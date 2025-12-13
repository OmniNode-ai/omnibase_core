"""
Typed metadata model for effect input/output.

This module provides strongly-typed metadata for effect patterns.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.protocols.base import LiteralEventPriority


class ModelEffectMetadata(BaseModel):
    """
    Typed metadata for effect input/output.

    Replaces dict[str, Any] metadata field in ModelEffectInput/Output
    with explicit typed fields for effect metadata.

    Note: All fields are optional as metadata may be partially populated
    depending on the source and context. This is intentional for metadata
    models that aggregate information from multiple sources.
    """

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
    environment: str | None = Field(
        default=None,
        description="Deployment environment",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    priority: LiteralEventPriority | None = Field(
        default=None,
        description="Operation priority (low, normal, high, critical)",
    )
    retry_count: int | None = Field(
        default=None,
        description="Number of retry attempts",
        ge=0,
    )


__all__ = ["ModelEffectMetadata"]
