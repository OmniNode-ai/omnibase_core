"""
Message queue connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError


class ModelMessageQueueProperties(BaseModel):
    """Message queue/broker-specific connection properties.
    Implements omnibase_spi protocols:
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelMessageQueueProperties"]
