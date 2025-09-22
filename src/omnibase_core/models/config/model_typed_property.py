"""
Typed property model for environment properties.

This module provides the ModelTypedProperty class for storing a single
typed property with validation in the environment property system.
"""

from __future__ import annotations

from typing import Any, TypeVar, cast

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_property_type import EnumPropertyType
from ...protocols_local.supported_property_value_protocol import (
    ProtocolSupportedPropertyValue,
)
from .model_property_metadata import ModelPropertyMetadata

# Use Any for property values since we support many types through the protocol
# All types must implement ProtocolSupportedPropertyValue (convertible to string)
# Using explicit Any type instead of type alias per ONEX standards

# Type variable for generic property handling
T = TypeVar("T", bound=ProtocolSupportedPropertyValue)


class ModelTypedProperty(BaseModel):
    """A single typed property with validation."""

    key: str = Field(description="Property key")
    value: Any = Field(description="Property value")
    metadata: ModelPropertyMetadata = Field(description="Property metadata")

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: Any) -> ProtocolSupportedPropertyValue:
        """Validate that value is of allowed type."""
        if isinstance(v, ProtocolSupportedPropertyValue):
            return v
        # For basic types, return as-is since they implement the protocol implicitly
        return cast(ProtocolSupportedPropertyValue, v)

    def get_typed_value(self, expected_type: type[T], default: T) -> T:
        """Get the value with specific type checking."""
        if isinstance(self.value, expected_type):
            return self.value
        return default

    def is_list_type(self) -> bool:
        """Check if this property stores a list value."""
        return self.metadata.property_type in [
            EnumPropertyType.STRING_LIST,
            EnumPropertyType.INTEGER_LIST,
            EnumPropertyType.FLOAT_LIST,
        ]

    def is_numeric_type(self) -> bool:
        """Check if this property stores a numeric value."""
        return self.metadata.property_type in [
            EnumPropertyType.INTEGER,
            EnumPropertyType.FLOAT,
        ]
