"""
Typed operation data model for effect input.

This module provides strongly-typed operation data for effect patterns,
using ModelQueryParameters and ModelEnvelopePayload for type-safe
parameter and event payload handling.

Security:
    - MAX_HEADERS: Maximum number of HTTP headers (100)
    - MAX_BODY_SIZE: Maximum request body size (1MB)
    - MAX_CONTENT_SIZE: Maximum file content size (10MB)
    - MAX_MESSAGE_SIZE: Maximum message queue message size (1MB)
"""

from __future__ import annotations

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants import MAX_URL_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
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

    Security:
    - String fields have max_length constraints to prevent memory exhaustion
    - Headers dict has max 100 entries to prevent DoS attacks
    - Body, content, and message fields have size limits
    """

    model_config = ConfigDict(
        extra="forbid", from_attributes=True, validate_assignment=True
    )

    # Security constants
    MAX_HEADERS: ClassVar[int] = 100
    MAX_BODY_SIZE: ClassVar[int] = 1_048_576  # 1MB
    MAX_CONTENT_SIZE: ClassVar[int] = 10_485_760  # 10MB
    MAX_MESSAGE_SIZE: ClassVar[int] = 1_048_576  # 1MB

    # Common fields across all effect types
    action: str | None = Field(
        default=None,
        description="Action to perform",
        max_length=256,
    )
    target: str | None = Field(
        default=None,
        description="Target resource for the operation",
        max_length=1024,
    )

    # Database operation fields
    table: str | None = Field(
        default=None,
        description="Database table name",
        max_length=256,
    )
    query: str | None = Field(
        default=None,
        description="Database query string",
        max_length=65536,  # 64KB for complex queries
    )
    parameters: ModelQueryParameters = Field(
        default_factory=ModelQueryParameters,
        description="Query parameters with typed values and query string support",
    )

    # API call fields
    url: str | None = Field(
        default=None,
        description="API endpoint URL",
        max_length=MAX_URL_LENGTH,
    )
    method: str | None = Field(
        default=None,
        description="HTTP method (GET, POST, PUT, DELETE)",
        max_length=16,
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
        max_length=4096,
    )
    content: str | None = Field(
        default=None,
        description="File content for write operations",
    )

    # Message queue fields
    queue_name: str | None = Field(
        default=None,
        description="Message queue name",
        max_length=256,
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

    @model_validator(mode="after")
    def _validate_sizes(self) -> Self:
        """Validate size constraints to prevent DoS attacks."""
        if len(self.headers) > self.MAX_HEADERS:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Headers dict exceeds maximum size of {self.MAX_HEADERS} entries",
                headers_count=len(self.headers),
                max_headers=self.MAX_HEADERS,
            )
        if self.body is not None and len(self.body) > self.MAX_BODY_SIZE:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Body exceeds maximum size of {self.MAX_BODY_SIZE} bytes",
                body_size=len(self.body),
                max_body_size=self.MAX_BODY_SIZE,
            )
        if self.content is not None and len(self.content) > self.MAX_CONTENT_SIZE:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Content exceeds maximum size of {self.MAX_CONTENT_SIZE} bytes",
                content_size=len(self.content),
                max_content_size=self.MAX_CONTENT_SIZE,
            )
        if self.message is not None and len(self.message) > self.MAX_MESSAGE_SIZE:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Message exceeds maximum size of {self.MAX_MESSAGE_SIZE} bytes",
                message_size=len(self.message),
                max_message_size=self.MAX_MESSAGE_SIZE,
            )
        return self


__all__ = ["ModelOperationData"]
