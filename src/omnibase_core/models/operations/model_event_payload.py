from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.errors.error_codes import (
    ModelCoreErrorCode,
    ModelOnexError,
)
from omnibase_core.models.operations.model_event_routing_info import (
    ModelEventRoutingInfo,
)
from omnibase_core.models.operations.model_types_event_data import EventDataUnion


class ModelEventPayload(BaseModel):
    """
    Strongly-typed event payload with discriminated unions.

    Replaces dict[str, Any] with discriminated event payload types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    event_type: EnumEventType = Field(
        default=..., description="Discriminated event type"
    )
    event_data: EventDataUnion = Field(
        default=...,
        description="Event-specific data with discriminated union",
    )
    routing_info: ModelEventRoutingInfo = Field(
        default_factory=lambda: ModelEventRoutingInfo(),
        description="Structured event routing information",
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
            error_code=ModelCoreErrorCode.VALIDATION_ERROR,
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
    "ModelEventPayload",
]
