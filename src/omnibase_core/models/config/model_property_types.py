"""
Property type definitions for environment properties.

This module provides strongly typed alternatives to overly broad Union types
for environment property storage with proper validation and constraints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Protocol, Type, TypeVar, Union, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, Field, validator


class PropertyTypeEnum(str, Enum):
    """Enum for supported property types."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    STRING_LIST = "string_list"
    INTEGER_LIST = "integer_list"
    FLOAT_LIST = "float_list"
    DATETIME = "datetime"
    UUID = "uuid"


@runtime_checkable
class ProtocolSupportedPropertyValue(Protocol):
    """Protocol for values that can be stored as environment properties."""

    def __str__(self) -> str:
        """Must be convertible to string."""
        ...


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


class ModelPropertyMetadata(BaseModel):
    """Metadata for individual properties."""

    description: str | None = Field(None, description="Property description")
    source: str | None = Field(None, description="Source of the property")
    property_type: PropertyTypeEnum = Field(description="Type of the property")
    required: bool = Field(default=False, description="Whether property is required")
    validation_pattern: str | None = Field(
        None, description="Regex pattern for validation"
    )
    min_value: float | None = Field(None, description="Minimum value for numeric types")
    max_value: float | None = Field(None, description="Maximum value for numeric types")
    allowed_values: list[str] | None = Field(
        None, description="Allowed values for enum-like properties"
    )


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


class ModelPropertyCollection(BaseModel):
    """Collection of typed properties with validation and helper methods."""

    properties: dict[str, ModelTypedProperty] = Field(
        default_factory=dict, description="Collection of typed properties"
    )

    def add_property(
        self,
        key: str,
        value: PropertyValue,
        property_type: PropertyTypeEnum,
        description: str | None = None,
        required: bool = False,
    ) -> None:
        """Add a new property with validation."""
        metadata = ModelPropertyMetadata(
            description=description,
            source=None,
            property_type=property_type,
            required=required,
            validation_pattern=None,
            min_value=None,
            max_value=None,
            allowed_values=None,
        )

        typed_property = ModelTypedProperty(key=key, value=value, metadata=metadata)
        self.properties[key] = typed_property

    def get_property(self, key: str) -> ModelTypedProperty | None:
        """Get a property by key."""
        return self.properties.get(key)

    def get_typed_value(
        self, key: str, expected_type: type[T], default: T | None = None
    ) -> T | None:
        """Get a property value with specific type checking."""
        prop = self.get_property(key)
        if prop is None:
            return default

        typed_value = prop.get_typed_value(expected_type)
        return typed_value if typed_value is not None else default

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value."""
        return self.get_typed_value(key, str, default) or default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value."""
        return self.get_typed_value(key, int, default) or default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float property value."""
        # Try float first, then int (which can be converted to float)
        value = self.get_typed_value(key, float, default)
        if value is None:
            int_value = self.get_typed_value(key, int, default)
            if int_value is not None:
                return float(int_value)
        return float(value) if value is not None else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value."""
        return self.get_typed_value(key, bool, default) or default

    def get_string_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get string list property value."""
        if default is None:
            default = []
        return self.get_typed_value(key, list, default) or default

    def get_required_properties(self) -> list[str]:
        """Get list of required property keys."""
        return [key for key, prop in self.properties.items() if prop.metadata.required]

    def validate_required_properties(self) -> list[str]:
        """Validate that all required properties are present and return missing ones."""
        required = self.get_required_properties()
        return [key for key in required if key not in self.properties]

    def get_properties_by_type(self, property_type: PropertyTypeEnum) -> list[str]:
        """Get property keys filtered by type."""
        return [
            key
            for key, prop in self.properties.items()
            if prop.metadata.property_type == property_type
        ]


# Export types for use
__all__ = [
    "PropertyValue",
    "PropertyTypeEnum",
    "ProtocolSupportedPropertyValue",
    "ModelPropertyMetadata",
    "ModelTypedProperty",
    "ModelPropertyCollection",
]
