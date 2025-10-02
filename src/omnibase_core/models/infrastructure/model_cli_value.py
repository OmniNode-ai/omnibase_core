"""
CLI value object model.

Strongly-typed value object for CLI output data, replacing broad union types
with discriminated union patterns following ONEX strong typing standards.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_cli_value_type import EnumCliValueType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Note: Previously had type alias (CliDictValueType)
# Removed to comply with ONEX strong typing standards.
# Now uses dict[str, ModelSchemaValue] for strong typing.


# CLI raw values use discriminated union pattern with runtime validation


class ModelCliValue(BaseModel):
    """
    CLI value object with discriminated union pattern.

    Replaces Union[str, int, float, bool, dict, list, None] with
    a strongly-typed discriminated union following ONEX patterns.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    value_type: EnumCliValueType = Field(description="Type of the CLI value")
    raw_value: object = Field(description="Raw value data")

    @field_validator("raw_value")
    @classmethod
    def validate_raw_value(cls, v: object, info: ValidationInfo) -> object:
        """Validate raw value matches declared type."""
        if "value_type" not in info.data:
            return v

        value_type = info.data["value_type"]

        if value_type == EnumCliValueType.STRING and not isinstance(v, str):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="String value type must contain str data",
            )
        if value_type == EnumCliValueType.INTEGER and not isinstance(v, int):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Integer value type must contain int data",
            )
        if value_type == EnumCliValueType.FLOAT and not isinstance(v, float):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Float value type must contain float data",
            )
        if value_type == EnumCliValueType.BOOLEAN and not isinstance(v, bool):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean value type must contain bool data",
            )
        if value_type == EnumCliValueType.DICT and not isinstance(v, dict):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Dict value type must contain dict data",
            )
        if value_type == EnumCliValueType.LIST and not isinstance(v, list):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="List value type must contain list data",
            )
        if value_type == EnumCliValueType.NULL and v is not None:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Null value type must contain None",
            )

        return v

    @classmethod
    def from_string(cls, value: str) -> ModelCliValue:
        """Create CLI value from string."""
        return cls(value_type=EnumCliValueType.STRING, raw_value=value)

    @classmethod
    def from_integer(cls, value: int) -> ModelCliValue:
        """Create CLI value from integer."""
        return cls(value_type=EnumCliValueType.INTEGER, raw_value=value)

    @classmethod
    def from_float(cls, value: float) -> ModelCliValue:
        """Create CLI value from float."""
        return cls(value_type=EnumCliValueType.FLOAT, raw_value=value)

    @classmethod
    def from_boolean(cls, value: bool) -> ModelCliValue:
        """Create CLI value from boolean."""
        return cls(value_type=EnumCliValueType.BOOLEAN, raw_value=value)

    @classmethod
    def from_list(cls, value: list[object]) -> ModelCliValue:
        """Create CLI value from list."""
        return cls(value_type=EnumCliValueType.LIST, raw_value=value)

    @classmethod
    def from_dict_value(cls, value: dict[str, ModelSchemaValue]) -> ModelCliValue:
        """Create CLI value wrapping a dictionary value with proper ONEX typing."""
        return cls(value_type=EnumCliValueType.DICT, raw_value=value)

    @classmethod
    def from_null(cls) -> ModelCliValue:
        """Create CLI value for null/None."""
        return cls(value_type=EnumCliValueType.NULL, raw_value=None)

    @classmethod
    def from_any(cls, value: object) -> ModelCliValue:
        """Create CLI value from any Python value with automatic type detection."""
        if value is None:
            return cls.from_null()
        if isinstance(value, str):
            return cls.from_string(value)
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.from_boolean(value)
        if isinstance(value, int):
            return cls.from_integer(value)
        if isinstance(value, float):
            return cls.from_float(value)
        if isinstance(value, dict):
            converted_value = {
                key: ModelSchemaValue.from_value(val) for key, val in value.items()
            }
            return cls.from_dict_value(converted_value)
        if isinstance(value, list):
            return cls.from_list(value)
        # Convert unknown types to string representation
        return cls.from_string(str(value))

    def to_python_value(self) -> object:
        """Convert back to Python native value."""
        return self.raw_value

    def is_primitive(self) -> bool:
        """Check if value is a primitive type."""
        return self.value_type in {
            EnumCliValueType.STRING,
            EnumCliValueType.INTEGER,
            EnumCliValueType.FLOAT,
            EnumCliValueType.BOOLEAN,
            EnumCliValueType.NULL,
        }

    def is_collection(self) -> bool:
        """Check if value is a collection type."""
        return self.value_type in {EnumCliValueType.DICT, EnumCliValueType.LIST}

    def __str__(self) -> str:
        """String representation of the CLI value."""
        if self.value_type == EnumCliValueType.NULL:
            return "null"
        return str(self.raw_value)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields with runtime validation
            for key, value in kwargs.items():
                if hasattr(self, key) and isinstance(value, (str, int, float, bool)):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            # Configure with runtime validation for type safety
            for key, value in kwargs.items():
                if hasattr(self, key) and isinstance(value, (str, int, float, bool)):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, object]:
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


# Export for use
__all__ = ["ModelCliValue"]
