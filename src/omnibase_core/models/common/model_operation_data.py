"""
Typed operation data model for effect input.

This module provides strongly-typed operation data for effect patterns,
using ModelQueryParameters and ModelEnvelopePayload for type-safe
parameter and event payload handling.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_envelope_payload import ModelEnvelopePayload
from omnibase_core.models.common.model_query_parameters import ModelQueryParameters


class ModelOperationData(BaseModel):
    """
    Typed operation data for effect input.

    Replaces dict[str, Any] operation_data field in ModelEffectInput
    with explicit typed fields for effect operations.

    Uses strongly-typed models for:
    - parameters: ModelQueryParameters with typed values and query string support
    - envelope_payload: ModelEnvelopePayload with event-specific typed fields
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    # Common fields across all effect types
    action: str | None = Field(
        default=None,
        description="Action to perform",
    )
    target: str | None = Field(
        default=None,
        description="Target resource for the operation",
    )

    # Database operation fields
    table: str | None = Field(
        default=None,
        description="Database table name",
    )
    query: str | None = Field(
        default=None,
        description="Database query string",
    )
    parameters: ModelQueryParameters = Field(
        default_factory=ModelQueryParameters,
        description="Query parameters with typed values and query string support",
    )

    # API call fields
    url: str | None = Field(
        default=None,
        description="API endpoint URL",
    )
    method: str | None = Field(
        default=None,
        description="HTTP method (GET, POST, PUT, DELETE)",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers as string key-value pairs",
    )
    body: str | None = Field(
        default=None,
        description="Request body as string",
    )

    # File operation fields
    path: str | None = Field(
        default=None,
        description="File system path",
    )
    content: str | None = Field(
        default=None,
        description="File content for write operations",
    )

    # Message queue fields
    queue_name: str | None = Field(
        default=None,
        description="Message queue name",
    )
    message: str | None = Field(
        default=None,
        description="Message content",
    )

    # Event envelope payload (for event-driven processing)
    envelope_payload: ModelEnvelopePayload = Field(
        default_factory=ModelEnvelopePayload,
        description="Event envelope payload with typed event fields",
    )


__all__ = ["ModelOperationData"]
