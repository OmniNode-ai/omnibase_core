"""
Property collection model for environment properties.

This module provides the ModelPropertyCollection class for managing
collections of typed properties with validation and helper methods.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field

from ...enums.enum_property_type import EnumPropertyType
from ...protocols_local.supported_property_value_protocol import (
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

    def add_string_property(
        self,
        key: str,
        value: str,
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add a string property with convenience method."""
        property_value = ModelPropertyValue.from_string(value, source)
        self.add_property(key, property_value, description, required)

    def add_int_property(
        self,
        key: str,
        value: int,
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add an integer property with convenience method."""
        property_value = ModelPropertyValue.from_int(value, source)
        self.add_property(key, property_value, description, required)

    def add_float_property(
        self,
        key: str,
        value: float,
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add a float property with convenience method."""
        property_value = ModelPropertyValue.from_float(value, source)
        self.add_property(key, property_value, description, required)

    def add_bool_property(
        self,
        key: str,
        value: bool,
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add a boolean property with convenience method."""
        property_value = ModelPropertyValue.from_bool(value, source)
        self.add_property(key, property_value, description, required)

    def add_list_property(
        self,
        key: str,
        value: list[str],
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add a string list property with convenience method."""
        property_value = ModelPropertyValue.from_string_list(value, source)
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

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value using type-safe accessor."""
        prop = self.get_property(key)
        if prop is None:
            return default
        try:
            return prop.value.as_string()
        except Exception:
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value using type-safe accessor."""
        prop = self.get_property(key)
        if prop is None:
            return default
        try:
            return prop.value.as_int()
        except Exception:
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float property value using type-safe accessor."""
        prop = self.get_property(key)
        if prop is None:
            return default
        try:
            return prop.value.as_float()
        except Exception:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value using type-safe accessor."""
        prop = self.get_property(key)
        if prop is None:
            return default
        try:
            return prop.value.as_bool()
        except Exception:
            return default

    def get_string_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get string list property value."""
        if default is None:
            default = []
        prop = self.get_property(key)
        if prop is None:
            return default

        # For list values, return the raw value if it's a list
        if isinstance(prop.value.value, list):
            return prop.value.value
        return default

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
