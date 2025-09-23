"""
Property collection model for environment properties.

This module provides the ModelPropertyCollection class for managing
collections of typed properties with validation and helper methods.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_property_type import EnumPropertyType
from omnibase_core.protocols_local.supported_property_value_protocol import (
    ProtocolSupportedPropertyValue,
)

from .model_property_metadata import ModelPropertyMetadata
from .model_property_value import ModelPropertyValue
from .model_typed_property import ModelTypedProperty

# Type variable for generic property handling
T = TypeVar("T", bound=ProtocolSupportedPropertyValue)


class ModelPropertyCollection(BaseModel):
    """Collection of typed properties with validation and helper methods."""

    properties: dict[str, ModelTypedProperty] = Field(
        default_factory=dict,
        description="Collection of typed properties",
    )

    def add_property(
        self,
        key: str,
        value: ModelPropertyValue,
        description: str | None = None,
        required: bool = False,
    ) -> None:
        """Add a new property using structured value."""
        metadata = ModelPropertyMetadata(
            description=description or "",
            source=value.source or "",
            property_type=value.value_type,
            required=required,
            validation_pattern="",
            min_value=None,
            max_value=None,
            allowed_values=[],
        )

        typed_property = ModelTypedProperty(key=key, value=value, metadata=metadata)
        self.properties[key] = typed_property

    def add_typed_property(
        self,
        key: str,
        value: T,
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add a typed property using generic type inference."""
        # Create ModelPropertyValue using appropriate factory method based on type
        if isinstance(value, str):
            property_value = ModelPropertyValue.from_string(value, source)
        elif isinstance(value, int):
            property_value = ModelPropertyValue.from_int(value, source)
        elif isinstance(value, float):
            property_value = ModelPropertyValue.from_float(value, source)
        elif isinstance(value, bool):
            property_value = ModelPropertyValue.from_bool(value, source)
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            property_value = ModelPropertyValue.from_string_list(value, source)
        elif isinstance(value, list) and all(isinstance(item, int) for item in value):
            property_value = ModelPropertyValue.from_int_list(value, source)
        elif isinstance(value, list) and all(isinstance(item, float) for item in value):
            property_value = ModelPropertyValue.from_float_list(value, source)
        else:
            msg = f"Unsupported property type: {type(value)}"
            raise ValueError(msg)

        self.add_property(key, property_value, description, required)

    def get_property(self, key: str) -> ModelTypedProperty | None:
        """Get a property by key."""
        return self.properties.get(key)

    def get_typed_value(self, key: str, expected_type: type[T], default: T) -> T:
        """Get a property value with specific type checking."""
        prop = self.get_property(key)
        if prop is None:
            return default

        return prop.get_typed_value(expected_type, default)

    def get_required_properties(self) -> list[str]:
        """Get list of required property keys."""
        return [key for key, prop in self.properties.items() if prop.metadata.required]

    def validate_required_properties(self) -> list[str]:
        """Validate that all required properties are present and return missing ones."""
        required = self.get_required_properties()
        return [key for key in required if key not in self.properties]

    def get_properties_by_type(self, property_type: EnumPropertyType) -> list[str]:
        """Get property keys filtered by type."""
        return [
            key
            for key, prop in self.properties.items()
            if prop.value.value_type == property_type
        ]
