"""
Property collection model for environment properties.

This module provides the ModelPropertyCollection class for managing
collections of typed properties with validation and helper methods.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, Field

from ...enums.enum_property_type import EnumPropertyType
from ...protocols.protocol_supported_property_value import (
    ProtocolSupportedPropertyValue,
)
from .model_property_metadata import ModelPropertyMetadata
from .model_typed_property import ModelTypedProperty

# Type variable for generic property handling
T = TypeVar("T", bound=ProtocolSupportedPropertyValue)


class ModelPropertyCollection(BaseModel):
    """Collection of typed properties with validation and helper methods."""

    properties: dict[str, ModelTypedProperty] = Field(
        default_factory=dict, description="Collection of typed properties"
    )

    def add_property(
        self,
        key: str,
        value: Any,
        property_type: EnumPropertyType,
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

    def get_typed_value(self, key: str, expected_type: type[T], default: T) -> T:
        """Get a property value with specific type checking."""
        prop = self.get_property(key)
        if prop is None:
            return default

        return prop.get_typed_value(expected_type, default)

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value."""
        return self.get_typed_value(key, str, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value."""
        return self.get_typed_value(key, int, default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float property value."""
        # Try float first, then int (which can be converted to float)
        prop = self.get_property(key)
        if prop is None:
            return default

        # Check if value is already a float
        if isinstance(prop.value, float):
            return prop.value
        # Convert int to float if needed
        elif isinstance(prop.value, int):
            return float(prop.value)

        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value."""
        return self.get_typed_value(key, bool, default)

    def get_string_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get string list property value."""
        if default is None:
            default = []
        return self.get_typed_value(key, list, default)

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
            if prop.metadata.property_type == property_type
        ]
