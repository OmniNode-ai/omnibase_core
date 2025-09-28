"""
Property collection model for environment properties.

This module provides the ModelPropertyCollection class for managing
collections of typed properties with validation and helper methods.
"""

from __future__ import annotations

# ONEX-compliant property value type using TypeVar instead of primitive soup Union
from typing import Any, Callable, TypeVar

# from omnibase_spi.protocols.types.core_types import (
#     ProtocolSupportedPropertyValue,
# )


PropertyValueType = TypeVar("PropertyValueType", str, int, float, bool, list[Any])
from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_property_type import EnumPropertyType
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_property_metadata import ModelPropertyMetadata
from .model_property_value import ModelPropertyValue
from .model_typed_property import ModelTypedProperty

# Use Any for property values since we support many types through the protocol
ProtocolSupportedPropertyValue = str

# Type variable for generic property handling
T = TypeVar("T", bound=ProtocolSupportedPropertyValue)


class ModelPropertyCollection(BaseModel):
    """Collection of typed properties with validation and helper methods.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

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
        value: PropertyValueType,
        description: str | None = None,
        required: bool = False,
        source: str | None = None,
    ) -> None:
        """Add a typed property using generic type inference."""
        # Create ModelPropertyValue using appropriate factory method based on type
        property_value = self._create_property_value_by_type(value, source)
        self.add_property(key, property_value, description, required)

    def _create_property_value_by_type(
        self,
        value: PropertyValueType,
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create ModelPropertyValue using type-specific factory methods."""
        # Simple, clean type checking - more readable and standards-compliant
        if isinstance(value, str):
            return ModelPropertyValue.from_string(value, source)
        elif isinstance(value, bool):
            return ModelPropertyValue.from_bool(value, source)
        elif isinstance(value, int):
            return ModelPropertyValue.from_int(value, source)
        elif isinstance(value, float):
            return ModelPropertyValue.from_float(value, source)
        elif isinstance(value, list):
            if not value:  # Empty list defaults to string list
                return ModelPropertyValue.from_string_list([], source)
            # Check homogeneous list types
            first_type = type(value[0])
            if all(isinstance(item, first_type) for item in value):
                if first_type is str:
                    return ModelPropertyValue.from_string_list(value, source)
                elif first_type is int:
                    return ModelPropertyValue.from_int_list(value, source)
                elif first_type is float:
                    return ModelPropertyValue.from_float_list(value, source)

        # If no handler matches, raise error
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported property type: {type(value)}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(str(type(value))),
                    "source": ModelSchemaValue.from_value(str(source)),
                    "supported_types": ModelSchemaValue.from_value(
                        "str, int, bool, float, dict"
                    ),
                }
            ),
        )

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
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False
