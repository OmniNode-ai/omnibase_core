"""
Typed operation data model for effect input.

This module provides strongly-typed operation data for effect patterns.
"""

from pydantic import BaseModel, Field


class ModelOperationData(BaseModel):
    """
    Typed operation data for effect input.

    Replaces dict[str, Any] operation_data field in ModelEffectInput
    with explicit typed fields for effect operations.
    """

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
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters",
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
        description="HTTP headers",
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
    envelope_payload: dict[str, str] = Field(
        default_factory=dict,
        description="Event envelope payload data",
    )


__all__ = ["ModelOperationData"]
