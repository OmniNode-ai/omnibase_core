"""
Typed metadata model for effect input/output.

This module provides strongly-typed metadata for effect patterns.
"""

from pydantic import BaseModel, Field


class ModelEffectMetadata(BaseModel):
    """
    Typed metadata for effect input/output.

    Replaces dict[str, Any] metadata field in ModelEffectInput/Output
    with explicit typed fields for effect metadata.
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
    environment: str | None = Field(
        default=None,
        description="Deployment environment",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    priority: str | None = Field(
        default=None,
        description="Operation priority",
    )
    retry_count: int | None = Field(
        default=None,
        description="Number of retry attempts",
        ge=0,
    )


__all__ = ["ModelEffectMetadata"]
