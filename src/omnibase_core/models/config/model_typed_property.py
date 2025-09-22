"""
Typed property model for environment properties.

This module provides the ModelTypedProperty class for storing a single
typed property with validation in the environment property system.
"""

from __future__ import annotations

from typing import TypeVar, cast

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_property_type import EnumPropertyType
from ...protocols_local.supported_property_value_protocol import (
    ProtocolSupportedPropertyValue,
)
from .model_property_metadata import ModelPropertyMetadata
from .model_property_value import ModelPropertyValue

# Use Any for property values since we support many types through the protocol
# All types must implement ProtocolSupportedPropertyValue (convertible to string)
# Using explicit Any type instead of type alias per ONEX standards

# Type variable for generic property handling
T = TypeVar("T", bound=ProtocolSupportedPropertyValue)


class ModelTypedProperty(BaseModel):
    """A single typed property with validation."""

    key: str = Field(description="Property key")
    value: ModelPropertyValue = Field(description="Structured property value")
    metadata: ModelPropertyMetadata = Field(description="Property metadata")

    @field_validator("value")
    @classmethod
    def validate_value_consistency(
        cls, v: ModelPropertyValue, info
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
            # Use ModelPropertyValue's type-safe accessors
            if expected_type == str:
                return cast(T, self.value.as_string())
            elif expected_type == int:
                return cast(T, self.value.as_int())
            elif expected_type == float:
                return cast(T, self.value.as_float())
            elif expected_type == bool:
                return cast(T, self.value.as_bool())
            elif isinstance(self.value.value, expected_type):
                return cast(T, self.value.value)
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

    def get_raw_value(self) -> ProtocolSupportedPropertyValue:
        """Get the raw value implementing the protocol."""
        return cast(ProtocolSupportedPropertyValue, self.value.value)
