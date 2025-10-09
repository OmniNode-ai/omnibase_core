from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_message_type import EnumMessageType
from omnibase_core.errors import EnumCoreErrorCode, ModelOnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.operations.model_command_message_content import (
    ModelCommandMessageContent,
)
from omnibase_core.models.operations.model_data_message_content import (
    ModelDataMessageContent,
)
from omnibase_core.models.operations.model_event_metadata import ModelEventMetadata
from omnibase_core.models.operations.model_message_content_base import (
    ModelMessageContentBase,
)
from omnibase_core.models.operations.model_message_headers import ModelMessageHeaders
from omnibase_core.models.operations.model_notification_message_content import (
    ModelNotificationMessageContent,
)
from omnibase_core.models.operations.model_query_message_content import (
    ModelQueryMessageContent,
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
    message_type: EnumMessageType = Field(
        default=...,
        description="Discriminated message type",
    )
    message_content: Annotated[
        ModelCommandMessageContent
        | ModelDataMessageContent
        | ModelNotificationMessageContent
        | ModelQueryMessageContent,
        Field(discriminator="message_type"),
    ] = Field(
        default=..., description="Message-specific content with discriminated union"
    )
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
        raise ModelOnexError(
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
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
    "ModelMessagePayload",
    "get_message_content_discriminator",
]
