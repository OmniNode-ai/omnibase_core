"""
Strongly-typed message payload structure.

Replaces dict[str, Any] usage in message payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.models.operations.model_event_metadata import ModelEventMetadata


# Message types (defined first as they're needed by other classes)
class ModelMessageType(str, Enum):
    """Message categories for proper routing and handling."""

    COMMAND = "command"
    DATA = "data"
    NOTIFICATION = "notification"
    QUERY = "query"


# Structured header types to replace primitive soup patterns (defined before ModelMessagePayload)
class ModelMessageHeaders(BaseModel):
    """Structured message headers."""

    content_type: str = Field(
        default="application/json",
        description="Message content type",
    )
    content_encoding: str = Field(default="utf-8", description="Content encoding")
    correlation_id: UUID | None = Field(
        default=None,
        description="Message correlation identifier",
    )
    reply_to: str = Field(default="", description="Reply destination")
    message_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Message schema version",
    )
    source_system: str = Field(default="", description="Source system identifier")
    destination_system: str = Field(
        default="",
        description="Destination system identifier",
    )
    security_token: str = Field(default="", description="Security authorization token")
    compression: str = Field(default="none", description="Message compression type")
    custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom headers",
    )


# Discriminated message content types (defined before ModelMessagePayload)
class ModelMessageContentBase(BaseModel):
    """Base message content with discriminator."""

    message_type: ModelMessageType = Field(
        ...,
        description="Message type discriminator",
    )
    content: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Structured message content with proper typing",
    )
    priority: str = Field(default="normal", description="Message priority level")
    expiration_time: datetime | None = Field(
        None,
        description="Message expiration time",
    )


class ModelCommandMessageContent(ModelMessageContentBase):
    """Command message content for action requests."""

    message_type: Literal[ModelMessageType.COMMAND] = Field(
        default=ModelMessageType.COMMAND,
        description="Command message type",
    )
    command_name: str = Field(..., description="Name of the command to execute")
    command_parameters: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Command parameters",
    )
    execution_mode: str = Field(
        default="synchronous",
        description="Command execution mode",
    )
    timeout_ms: int = Field(
        default=30000,
        description="Command timeout in milliseconds",
    )
    retry_policy: dict[str, int] = Field(
        default_factory=dict,
        description="Command retry policy configuration",
    )


class ModelDataMessageContent(ModelMessageContentBase):
    """Data message content for information transfer."""

    message_type: Literal[ModelMessageType.DATA] = Field(
        default=ModelMessageType.DATA,
        description="Data message type",
    )
    data_type: str = Field(..., description="Type of data being transferred")
    data_schema: str = Field(..., description="Schema identifier for data validation")
    compression_used: bool = Field(
        default=False,
        description="Whether data is compressed",
    )
    checksum: str = Field(default="", description="Data integrity checksum")
    encoding: str = Field(default="utf-8", description="Data encoding format")


class ModelNotificationMessageContent(ModelMessageContentBase):
    """Notification message content for event notifications."""

    message_type: Literal[ModelMessageType.NOTIFICATION] = Field(
        default=ModelMessageType.NOTIFICATION,
        description="Notification message type",
    )
    notification_category: str = Field(..., description="Category of the notification")
    severity_level: str = Field(
        default="info",
        description="Notification severity level",
    )
    action_required: bool = Field(
        default=False,
        description="Whether action is required",
    )
    recipients: list[str] = Field(
        default_factory=list,
        description="Notification recipients",
    )
    delivery_channels: list[str] = Field(
        default_factory=list,
        description="Delivery channels to use",
    )


class ModelQueryMessageContent(ModelMessageContentBase):
    """Query message content for information requests."""

    message_type: Literal[ModelMessageType.QUERY] = Field(
        default=ModelMessageType.QUERY,
        description="Query message type",
    )
    query_type: str = Field(..., description="Type of query being performed")
    query_parameters: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Query parameters",
    )
    result_format: str = Field(default="json", description="Expected result format")
    max_results: int = Field(default=100, description="Maximum number of results")
    include_metadata: bool = Field(
        default=True,
        description="Whether to include result metadata",
    )


# Discriminator function for message content union
def get_message_content_discriminator(v: dict[str, Any] | BaseModel) -> str:
    """Discriminator function for message content types."""
    if isinstance(v, dict):
        return str(v.get("message_type", "data"))
    if hasattr(v, "message_type"):
        return str(v.message_type)
    return "data"


# Main message payload class (defined after all dependencies)
class ModelMessagePayload(BaseModel):
    """
    Strongly-typed message payload with discriminated unions.

    Replaces dict[str, Any] with discriminated message payload types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    message_id: UUID = Field(
        default_factory=uuid4,
        description="Unique message identifier (UUID format)",
    )
    message_type: ModelMessageType = Field(
        ...,
        description="Discriminated message type",
    )
    message_content: Annotated[
        ModelCommandMessageContent
        | ModelDataMessageContent
        | ModelNotificationMessageContent
        | ModelQueryMessageContent,
        Field(discriminator="message_type"),
    ] = Field(..., description="Message-specific content with discriminated union")
    headers: ModelMessageHeaders = Field(
        default_factory=ModelMessageHeaders,
        description="Structured message headers",
    )
    metadata: ModelEventMetadata = Field(
        default_factory=lambda: ModelEventMetadata(
            event_id=uuid4(),
            event_type="message",
            source="system",
        ),
        description="Event metadata for the message",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = [
    "ModelCommandMessageContent",
    "ModelDataMessageContent",
    "ModelMessageContentBase",
    "ModelMessageHeaders",
    "ModelMessagePayload",
    "ModelMessageType",
    "ModelNotificationMessageContent",
    "ModelQueryMessageContent",
]
