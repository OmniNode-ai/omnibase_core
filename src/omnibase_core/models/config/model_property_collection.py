"""
Property collection model for environment properties.

This module provides the ModelPropertyCollection class for managing
collections of typed properties with validation and helper methods.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, Field

# Use already imported ModelPropertyValue for type safety
# No need for primitive soup fallback - ModelPropertyValue provides proper discriminated union
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_property_type import EnumPropertyType
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_property_metadata import ModelPropertyMetadata

# Import PropertyValueType from the proper discriminated union model
from .model_property_value import ModelPropertyValue, PropertyValueType
from .model_typed_property import ModelTypedProperty

# Type variable for generic property handling
T = TypeVar("T", bound=PropertyValueType)


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
        # Define type handlers as a list of (checker_function, factory_method) tuples
        # Order matches original elif chain to preserve existing behavior
        # Use object instead of Any for type dispatch pattern
        TypeChecker = Callable[[object], bool]
        FactoryMethod = Callable[[object, str | None], ModelPropertyValue]

        type_handlers: list[tuple[TypeChecker, FactoryMethod]] = [
            (lambda v: isinstance(v, str), ModelPropertyValue.from_string),  # type: ignore[list-item]
            (lambda v: isinstance(v, int), ModelPropertyValue.from_int),  # type: ignore[list-item]
            (lambda v: isinstance(v, float), ModelPropertyValue.from_float),  # type: ignore[list-item]
            (lambda v: isinstance(v, bool), ModelPropertyValue.from_bool),  # type: ignore[list-item]
            (
                lambda v: isinstance(v, list)
                and all(isinstance(item, str) for item in v),
                ModelPropertyValue.from_string_list,  # type: ignore[list-item]
            ),
            (
                lambda v: isinstance(v, list)
                and all(isinstance(item, int) for item in v),
                ModelPropertyValue.from_int_list,  # type: ignore[list-item]
            ),
            (
                lambda v: isinstance(v, list)
                and all(isinstance(item, float) for item in v),
                ModelPropertyValue.from_float_list,  # type: ignore[list-item]
            ),
        ]

        # Find the appropriate handler
        for type_checker, factory_method in type_handlers:
            if type_checker(value):
                return factory_method(value, source)

        # If no handler matches, raise error
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported property type: {type(value)}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(str(type(value))),
                    "source": ModelSchemaValue.from_value(str(source)),
                    "supported_types": ModelSchemaValue.from_value(
                        "str, int, bool, float, dict",
                    ),
                },
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
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
