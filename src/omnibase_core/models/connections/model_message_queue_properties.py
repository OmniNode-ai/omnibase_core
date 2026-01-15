"""
Message queue connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelMessageQueueProperties(BaseModel):
    """Message queue/broker-specific connection properties.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # Entity references with UUID + display name pattern
    queue_id: UUID | None = Field(default=None, description="Queue UUID reference")
    queue_display_name: str | None = Field(
        default=None,
        description="Queue display name",
    )
    exchange_id: UUID | None = Field(
        default=None,
        description="Exchange UUID reference",
    )
    exchange_display_name: str | None = Field(
        default=None,
        description="Exchange display name",
    )

    # Queue configuration
    routing_key: str | None = Field(default=None, description="Routing key")
    durable: bool | None = Field(default=None, description="Durable queue/exchange")

    def get_queue_identifier(self) -> str | None:
        """Get queue identifier for display purposes."""
        if self.queue_display_name:
            return self.queue_display_name
        if self.queue_id:
            return str(self.queue_id)
        return None

    def get_exchange_identifier(self) -> str | None:
        """Get exchange identifier for display purposes."""
        if self.exchange_display_name:
            return self.exchange_display_name
        if self.exchange_id:
            return str(self.exchange_id)
        return None

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValidationError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Pydantic handles validation automatically during instantiation.
        # This method exists to satisfy the ProtocolValidatable interface.
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelMessageQueueProperties"]
