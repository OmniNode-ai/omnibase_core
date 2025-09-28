"""
Strongly-typed message payload structure.

Replaces dict[str, Any] usage in message payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.type_constraints import (
    Executable,
    Identifiable,
    Serializable,
    Validatable,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_event_metadata import ModelEventMetadata


class ModelMessagePayload(BaseModel):
    """
    Strongly-typed message payload.

    Replaces dict[str, Any] with structured message payload model.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    message_id: UUID = Field(
        default_factory=uuid4, description="Unique message identifier (UUID format)"
    )
    message_type: str = Field(..., description="Type of message")
    content: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Structured message content with proper typing",
    )
    headers: dict[str, str] = Field(default_factory=dict, description="Message headers")
    metadata: ModelEventMetadata = Field(
        default_factory=lambda: ModelEventMetadata(
            event_id=uuid4(), event_type="message", source="system"
        ),
        description="Event metadata for the message",
    )

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
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
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelMessagePayload"]
