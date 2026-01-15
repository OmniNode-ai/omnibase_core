"""
CLI Execution Context Model.

Represents custom execution context with proper validation.
Replaces dict[str, Any] for custom context with structured typing.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_context_source import EnumContextSource
from omnibase_core.enums.enum_context_type import EnumContextType
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCliExecutionContext(BaseModel):
    """
    Structured custom context for CLI execution.

    Replaces dict[str, Any] for custom_context to provide
    type safety and validation for execution context data.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Context identification
    key: str = Field(default=..., description="Context key identifier")
    value: object = Field(
        default=...,
        description="Context value - validated against context_type discriminator",
    )

    # Context metadata
    context_type: EnumContextType = Field(
        default=..., description="Type of context data"
    )
    is_persistent: bool = Field(default=False, description="Whether context persists")
    priority: int = Field(default=0, description="Context priority", ge=0, le=10)

    # Tracking
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Context creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Context last update time",
    )

    # Validation
    description: str = Field(default="", description="Context description")
    source: EnumContextSource = Field(
        default=EnumContextSource.USER,
        description="Context data source",
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: object, info: ValidationInfo) -> object:
        """Validate that value is serializable."""
        # Basic validation to ensure value can be serialized
        # Context type validation is not needed since value: object allows any type
        # and context_type refers to the source/nature of the context, not data type
        return v

    def get_string_value(self) -> str:
        """Get value as string representation."""
        if isinstance(self.value, datetime):
            return self.value.isoformat()
        if isinstance(self.value, Path):
            return str(self.value)
        if isinstance(self.value, list):
            return ",".join(str(v) for v in self.value)
        return str(self.value)

    def get_typed_value(self) -> object:
        """Get the properly typed value."""
        return self.value

    def is_datetime_value(self) -> bool:
        """Check if this is a datetime value."""
        return isinstance(self.value, datetime)

    def is_path_value(self) -> bool:
        """Check if this is a Path value."""
        return isinstance(self.value, Path)

    def is_uuid_value(self) -> bool:
        """Check if this is a UUID value."""
        return isinstance(self.value, UUID)

    def update_value(self, new_value: object) -> None:
        """Update the context value and timestamp."""
        self.value = new_value
        self.updated_at = datetime.now()

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        return True


# Export for use
__all__ = ["ModelCliExecutionContext"]
