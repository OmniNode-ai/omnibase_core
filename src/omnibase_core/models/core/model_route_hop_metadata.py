"""
Route hop metadata model.

Provides typed metadata for route hop entries in routing audit trails.
"""

from pydantic import BaseModel, Field


class ModelRouteHopMetadata(BaseModel):
    """
    Typed model for route hop metadata.

    Replaces dict[str, Any] metadata field in ModelRouteHop with
    strongly-typed fields for hop-specific information.
    """

    # Routing context
    route_version: str | None = Field(  # string-version-ok: routing rules version
        default=None,
        description="Version of the routing rules applied",
    )
    routing_table_id: str | None = Field(  # string-id-ok: routing table identifier
        default=None,
        description="Identifier of the routing table used",
    )

    # Performance metrics
    queue_wait_time_ms: int | None = Field(
        default=None,
        description="Time spent waiting in queue (ms)",
        ge=0,
    )
    serialization_time_ms: int | None = Field(
        default=None,
        description="Time spent on serialization (ms)",
        ge=0,
    )

    # Message context
    message_size_bytes: int | None = Field(
        default=None,
        description="Size of the message in bytes",
        ge=0,
    )
    compression_ratio: float | None = Field(
        default=None,
        description="Compression ratio applied (if any)",
        ge=0.0,
        le=1.0,
    )

    # Debug information
    debug_trace: str | None = Field(
        default=None,
        description="Debug trace information",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with this hop",
    )

    # Custom string values for extensibility
    custom_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom string metadata fields",
    )


__all__ = ["ModelRouteHopMetadata"]
