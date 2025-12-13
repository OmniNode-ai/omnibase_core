"""
Typed payload model for intent declarations.

This module provides strongly-typed payloads for intent patterns.
"""

from pydantic import BaseModel, Field


class ModelIntentPayload(BaseModel):
    """
    Typed payload for intent declarations.

    Replaces dict[str, Any] payload field in ModelIntent
    with explicit typed fields for intent payloads.
    """

    # Event emission fields
    event_type: str | None = Field(
        default=None,
        description="Event type to emit",
    )
    event_data: dict[str, str] = Field(
        default_factory=dict,
        description="Event data as key-value pairs",
    )

    # Logging fields
    log_level: str | None = Field(
        default=None,
        description="Log level (debug, info, warn, error)",
    )
    log_message: str | None = Field(
        default=None,
        description="Log message content",
    )

    # Storage fields
    storage_key: str | None = Field(
        default=None,
        description="Storage key for write operations",
    )
    storage_value: str | None = Field(
        default=None,
        description="Value to store",
    )

    # Notification fields
    notification_type: str | None = Field(
        default=None,
        description="Type of notification",
    )
    recipients: list[str] = Field(
        default_factory=list,
        description="Notification recipients",
    )
    subject: str | None = Field(
        default=None,
        description="Notification subject",
    )
    body: str | None = Field(
        default=None,
        description="Notification body",
    )

    # HTTP request fields
    url: str | None = Field(
        default=None,
        description="HTTP request URL",
    )
    method: str | None = Field(
        default=None,
        description="HTTP method",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers",
    )
    request_body: str | None = Field(
        default=None,
        description="HTTP request body",
    )


__all__ = ["ModelIntentPayload"]
