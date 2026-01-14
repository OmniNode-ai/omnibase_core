"""
Strongly-typed event metadata structure.

Replaces dict[str, Any] usage in event metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelEventMetadata(BaseModel):
    """
    Strongly-typed event metadata.

    Replaces dict[str, Any] with structured event metadata model.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Mutability Note:
        This model is intentionally mutable (not frozen) to support the execute()
        protocol method which updates event processing state (processed, retry_count,
        processing_duration_ms) during event handling. The validate_assignment=True
        setting ensures type safety is maintained when fields are modified.

        For thread-safe access in concurrent scenarios, callers should use appropriate
        synchronization mechanisms or create immutable copies when sharing across threads.
    """

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique event identifier (UUID format)",
    )
    event_type: str = Field(default=..., description="Type of event")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp",
    )
    source: str = Field(default=..., description="Event source identifier")

    # Event processing
    processed: bool = Field(default=False, description="Whether event was processed")
    processing_duration_ms: int = Field(
        default=0, ge=0, description="Processing duration"
    )
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")

    # Event routing
    target_handlers: dict[str, str] = Field(
        default_factory=dict,
        description="Target event handlers",
    )
    routing_key: str = Field(default="", description="Event routing key")

    # Context information
    user_id: UUID | None = Field(
        default=None,
        description="User identifier (UUID format)",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Session identifier (UUID format)",
    )
    request_id: UUID | None = Field(
        default=None,
        description="Request identifier (UUID format)",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
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
            message=f"{self.__class__.__name__} must have a valid ID field (type_id, id, uuid, identifier, etc.). Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelEventMetadata"]
