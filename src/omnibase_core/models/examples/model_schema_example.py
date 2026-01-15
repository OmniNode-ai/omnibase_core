"""
Schema example model.

Type-safe model for extracting examples from YAML schema files,
replacing dict[str, Any] return types with structured models.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict

# Note: Using ModelSchemaValue instead of complex union types for type safety

# Type variable for generic methods
T = TypeVar("T")


class ModelSchemaExample(BaseModel):
    """
    Type-safe model for schema examples.

    Replaces dict[str, Any] returns from extract_example_from_schema
    with properly structured and validated data.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core example data - using existing typed properties pattern
    example_data: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Type-safe example data from schema",
    )

    # Metadata about the example
    example_index: int = Field(
        description="Index of this example in the schema examples array",
    )

    schema_path: str = Field(
        description="Path to the schema file this example was extracted from",
    )

    # Optional validation info
    data_format: EnumDataType = Field(
        default=EnumDataType.YAML,
        description="Format of the example data",
    )

    schema_version: ModelSemVer | None = Field(
        default=None,
        description="Schema version if available",
    )

    is_validated: bool = Field(
        default=False,
        description="Whether example has been validated against schema",
    )

    def has_data(self) -> bool:
        """Check if example contains any data."""
        return not self.example_data.is_empty()

    def get_value(self, key: str, default: T) -> T:
        """
        Get typed value with proper default handling.

        Args:
            key: The key to look up
            default: Default value to return if key not found or type mismatch

        Returns:
            Value of the requested type or default
        """
        schema_value_result = self.example_data.get_custom_value_wrapped(key)
        if schema_value_result.is_err():
            return default

        # Extract raw value from ModelSchemaValue
        schema_value = schema_value_result.unwrap()
        raw_value = schema_value.to_value()

        # Type check against default type
        if isinstance(raw_value, type(default)):
            return raw_value

        return default

    def set_value(self, key: str, value: object) -> None:
        """
        Set typed value in example data.

        Args:
            key: The key to set
            value: The value to store (raw primitive type)
        """
        # The set_custom_value method handles runtime type validation
        try:
            self.example_data.set_custom_value(key, value)
        except ModelOnexError:
            # Re-raise validation errors from set_custom_value
            raise

    def get_all_keys(self) -> list[str]:
        """Get all keys from example data."""
        return list(self.example_data.get_all_custom_fields().keys())

    def get_raw_value(self, key: str) -> object:
        """
        Get raw value without type checking.

        Args:
            key: The key to look up

        Returns:
            Raw Python value or None if not found
        """
        schema_value_result = self.example_data.get_custom_value_wrapped(key)
        if schema_value_result.is_err():
            return None
        schema_value = schema_value_result.unwrap()
        return schema_value.to_value()

    def set_raw_value(self, key: str, value: object) -> None:
        """
        Set raw value (any type) in example data.

        Args:
            key: The key to set
            value: The value to store (raw primitive type)
        """
        # The set_custom_value method handles runtime type validation
        try:
            self.example_data.set_custom_value(key, value)
        except ModelOnexError:
            # Re-raise validation errors from set_custom_value
            raise

    def update_from_dict(self, data: dict[str, ModelSchemaValue]) -> None:
        """
        Update example data from a dictionary.

        Args:
            data: Dictionary of ModelSchemaValue objects to add to example data
        """
        for key, value in data.items():
            # Extract raw value from ModelSchemaValue and pass to set_custom_value
            raw_value = value.to_value()
            # The set_custom_value method handles runtime type validation
            try:
                self.example_data.set_custom_value(key, raw_value)
            except ModelOnexError:
                # Skip values that aren't supported primitive types
                pass

    def get_example_data_as_dict(self) -> dict[str, ModelSchemaValue]:
        """
        Get example data as a dictionary of ModelSchemaValue objects.

        Note: This method returns ModelSchemaValue objects directly.
        For raw Python values, use .get_raw_value() on individual keys.

        Returns:
            Dictionary with all example data as ModelSchemaValue objects
        """
        result = {}
        for key in self.get_all_keys():
            schema_value_result = self.example_data.get_custom_value_wrapped(key)
            if schema_value_result.is_ok():
                result[key] = schema_value_result.unwrap()
        return result

    @classmethod
    def create_from_dict(
        cls,
        data: dict[str, ModelSchemaValue],
        example_index: int,
        schema_path: str,
        data_format: EnumDataType = EnumDataType.YAML,
        schema_version: ModelSemVer | None = None,
    ) -> ModelSchemaExample:
        """
        Create ModelSchemaExample from a dictionary.

        Args:
            data: Dictionary data to store as example
            example_index: Index of this example
            schema_path: Path to the schema file
            data_format: Format of the example data
            schema_version: Schema version if available

        Returns:
            New ModelSchemaExample instance
        """
        # Create custom properties from ModelSchemaValue data
        custom_props = ModelCustomProperties()
        for key, value in data.items():
            # Extract raw value from ModelSchemaValue and pass to set_custom_value
            raw_value = value.to_value()
            # The set_custom_value method handles runtime type validation
            try:
                custom_props.set_custom_value(key, raw_value)
            except ModelOnexError:
                # Skip values that aren't supported primitive types
                pass

        return cls(
            example_data=custom_props,
            example_index=example_index,
            schema_path=schema_path,
            data_format=data_format,
            schema_version=schema_version,
        )

    @classmethod
    def create_empty(
        cls,
        example_index: int,
        schema_path: str,
        data_format: EnumDataType = EnumDataType.YAML,
    ) -> ModelSchemaExample:
        """
        Create an empty ModelSchemaExample.

        Args:
            example_index: Index of this example
            schema_path: Path to the schema file
            data_format: Format of the example data

        Returns:
            New empty ModelSchemaExample instance
        """
        return cls(
            example_data=ModelCustomProperties(),
            example_index=example_index,
            schema_path=schema_path,
            data_format=data_format,
            schema_version=None,
        )

    def validate_example(self) -> bool:
        """
        Validate the example data.

        Returns:
            True if validation passes, False otherwise
        """
        # Basic validation - ensure we have some data
        if self.example_data.is_empty():
            return False

        # Mark as validated if checks pass
        self.is_validated = True
        return True

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Returns True for well-constructed instances. Override in subclasses
        for custom validation logic.
        """
        # Basic validation - Pydantic handles field constraints
        # Override in specific models for custom validation
        return True


__all__ = ["ModelSchemaExample"]
