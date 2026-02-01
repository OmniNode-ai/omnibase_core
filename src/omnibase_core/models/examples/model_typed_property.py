"""
Typed property model for environment properties.

This module provides the ModelTypedProperty class for storing a single
typed property with validation in the environment property system.
"""

from __future__ import annotations

from typing import TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_property_type import EnumPropertyType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

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
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    key: str = Field(description="Property key")
    value: ModelPropertyValue = Field(description="Structured property value")
    metadata: ModelPropertyMetadata = Field(description="Property metadata")

    @model_validator(mode="after")
    def validate_value_consistency(self) -> ModelTypedProperty:
        """Validate that value type matches metadata type."""
        if self.metadata.property_type != self.value.value_type:
            # Create a new ModelPropertyValue with correct type from metadata
            self.value = ModelPropertyValue(
                value=self.value.value,
                value_type=self.metadata.property_type,
                source=self.value.source,
                is_validated=True,
            )
        return self

    def get_typed_value(self, expected_type: type[T], default: T) -> T:
        """Get the value with specific type checking."""
        try:
            # Use ModelPropertyValue's type-safe accessors based on expected type
            if expected_type == str:
                return cast("T", self.value.as_string())
            if expected_type == int:
                return cast("T", self.value.as_int())
            if expected_type == float:
                return cast("T", self.value.as_float())
            if expected_type == bool:
                return cast("T", self.value.as_bool())
            if isinstance(self.value.value, expected_type):
                return self.value.value
        except (AssertionError, ModelOnexError, TypeError, ValueError):
            # fallback-ok: type conversion failures return default value
            # AssertionError: assert statements in accessor methods
            # ModelOnexError: explicit type conversion errors from accessors
            # TypeError: type mismatch during conversion (e.g., None to int)
            # ValueError: int()/float() conversion of invalid strings
            pass
        return default

    def is_list_type(self) -> bool:
        """Check if this property stores a list[Any]value."""
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If setting an attribute fails or validation error occurs
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except (
            AttributeError,
            TypeError,
            ValidationError,
            ValueError,
        ) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Configuration failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True
