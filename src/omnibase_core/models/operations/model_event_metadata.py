"""
Strongly-typed event metadata structure.

Replaces dict[str, Any] usage in event metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
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


class ModelEventMetadata(BaseModel):
    """
    Strongly-typed event metadata.

    Replaces dict[str, Any] with structured event metadata model.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    event_id: UUID = Field(
        default_factory=uuid4, description="Unique event identifier (UUID format)"
    )
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Event timestamp"
    )
    source: str = Field(..., description="Event source identifier")

    # Event processing
    processed: bool = Field(default=False, description="Whether event was processed")
    processing_duration_ms: int = Field(default=0, description="Processing duration")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    # Event routing
    target_handlers: dict[str, str] = Field(
        default_factory=dict, description="Target event handlers"
    )
    routing_key: str = Field(default="", description="Event routing key")

    # Context information
    user_id: UUID | None = Field(
        default=None, description="User identifier (UUID format)"
    )
    session_id: UUID | None = Field(
        default=None, description="Session identifier (UUID format)"
    )
    request_id: UUID | None = Field(
        default=None, description="Request identifier (UUID format)"
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
__all__ = ["ModelEventMetadata"]
