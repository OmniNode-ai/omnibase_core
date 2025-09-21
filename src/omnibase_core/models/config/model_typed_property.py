"""
Typed property model for environment properties.

This module provides the ModelTypedProperty class for storing a single
typed property with validation in the environment property system.
"""

from datetime import datetime
from typing import TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from ...enums.enum_property_type import PropertyTypeEnum
from ...protocols.protocol_supported_property_value import (
    ProtocolSupportedPropertyValue,
)
from .model_property_metadata import ModelPropertyMetadata

# Define the specific union type for property values with constraints
PropertyValue = Union[
    str,
    int,
    bool,
    float,
    list[str],
    list[int],
    list[float],
    datetime,
    UUID,
]

# Type variable for generic property handling
T = TypeVar("T", bound=ProtocolSupportedPropertyValue)


class ModelTypedProperty(BaseModel):
    """A single typed property with validation."""

    key: str = Field(description="Property key")
    value: PropertyValue = Field(description="Property value")
    metadata: ModelPropertyMetadata = Field(description="Property metadata")

    @validator("value")
    def validate_value_type(cls, v: PropertyValue) -> PropertyValue:
        """Validate that value is of allowed PropertyValue type."""
        return v

    def get_typed_value(self, expected_type: type[T]) -> T | None:
        """Get the value with specific type checking."""
        if isinstance(self.value, expected_type):
            return self.value
        return None

    def is_list_type(self) -> bool:
        """Check if this property stores a list value."""
        return self.metadata.property_type in [
            PropertyTypeEnum.STRING_LIST,
            PropertyTypeEnum.INTEGER_LIST,
            PropertyTypeEnum.FLOAT_LIST,
        ]

    def is_numeric_type(self) -> bool:
        """Check if this property stores a numeric value."""
        return self.metadata.property_type in [
            PropertyTypeEnum.INTEGER,
            PropertyTypeEnum.FLOAT,
        ]
