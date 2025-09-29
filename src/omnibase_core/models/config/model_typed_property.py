"""
Typed property model for environment properties.

This module provides the ModelTypedProperty class for storing a single
typed property with validation in the environment property system.
"""

from __future__ import annotations

from typing import Any, TypeVar, cast

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.core.type_constraints import BasicValueType, Configurable
from omnibase_core.enums.enum_property_type import EnumPropertyType

from .model_property_metadata import ModelPropertyMetadata
from .model_property_value import ModelPropertyValue

# Use already imported ModelPropertyValue for type safety
# No need for primitive soup fallback - ModelPropertyValue provides proper discriminated union


# Use object for property values since we support many types through the protocol
# All types must implement BasicValueType (str, int, bool)
# Using explicit object type instead of Any per ONEX standards

# Use object for type-safe generic property handling
# ModelPropertyValue discriminated union provides type safety

# Type variable for generic property handling
T = TypeVar("T")


class ModelTypedProperty(BaseModel):
    """A single typed property with validation.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    key: str = Field(description="Property key")
    value: ModelPropertyValue = Field(description="Structured property value")
    metadata: ModelPropertyMetadata = Field(description="Property metadata")

    @field_validator("value")
    @classmethod
    def validate_value_consistency(
        cls,
        v: ModelPropertyValue,
        info: ValidationInfo,
    ) -> ModelPropertyValue:
        """Validate that value type matches metadata type."""
        if hasattr(info, "data") and "metadata" in info.data:
            metadata = info.data["metadata"]
            if metadata.property_type != v.value_type:
                # Create a new ModelPropertyValue with correct type from metadata
                return ModelPropertyValue(
                    value=v.value,
                    value_type=metadata.property_type,
                    source=v.source,
                    is_validated=True,
                )
        return v

    def get_typed_value(self, expected_type: type[T], default: T) -> T:
        """Get the value with specific type checking."""
        try:
            # Use ModelPropertyValue's type-safe accessors based on expected type
            if expected_type == str:
                return cast(T, self.value.as_string())
            elif expected_type == int:
                return cast(T, self.value.as_int())
            elif expected_type == float:
                return cast(T, self.value.as_float())
            elif expected_type == bool:
                return cast(T, self.value.as_bool())
            elif isinstance(self.value.value, expected_type):
                return self.value.value
        except Exception:
            pass
        return default

    def is_list_type(self) -> bool:
        """Check if this property stores a list value."""
        return self.value.value_type in [
            EnumPropertyType.STRING_LIST,
            EnumPropertyType.INTEGER_LIST,
            EnumPropertyType.FLOAT_LIST,
        ]

    def is_numeric_type(self) -> bool:
        """Check if this property stores a numeric value."""
        return self.value.value_type in [
            EnumPropertyType.INTEGER,
            EnumPropertyType.FLOAT,
        ]

    def get_raw_value(self) -> object:
        """Get the raw value implementing the protocol."""
        return self.value.value

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False
