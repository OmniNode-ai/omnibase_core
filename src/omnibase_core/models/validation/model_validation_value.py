"""
Validation value object model.

Strongly-typed value object for validation details, replacing union types
with discriminated union patterns following ONEX strong typing standards.
"""

from __future__ import annotations

from typing import Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator

# ONEX type alias for validation values (replaces Any)
ValidationValueType = Union[str, int, bool, None]
# Extended type for input values that may need conversion
InputValueType = Union[str, int, float, bool, None, list[object], dict[str, object]]

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_value_type import EnumValidationValueType
from omnibase_core.exceptions.onex_error import OnexError


class ModelValidationValue(BaseModel):
    """
    Validation value object with discriminated union pattern.

    Replaces str | int | bool unions in validation details with
    a strongly-typed discriminated union following ONEX patterns.
    """

    value_type: EnumValidationValueType = Field(
        description="Type of the validation value",
    )
    raw_value: ValidationValueType = Field(description="Raw value data")

    @field_validator("raw_value")
    @classmethod
    def validate_raw_value(
        cls,
        v: ValidationValueType,
        info: ValidationInfo,
    ) -> ValidationValueType:
        """Validate raw value matches declared type."""
        if not hasattr(info, "data") or "value_type" not in info.data:
            return v

        value_type = info.data["value_type"]

        if value_type == EnumValidationValueType.STRING and not isinstance(v, str):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="String validation value must contain str data",
            )
        if value_type == EnumValidationValueType.INTEGER and not isinstance(v, int):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Integer validation value must contain int data",
            )
        if value_type == EnumValidationValueType.BOOLEAN and not isinstance(v, bool):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean validation value must contain bool data",
            )
        if value_type == EnumValidationValueType.NULL and v is not None:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Null validation value must contain None",
            )

        return v

    @classmethod
    def from_string(cls, value: str) -> ModelValidationValue:
        """Create validation value from string."""
        return cls(value_type=EnumValidationValueType.STRING, raw_value=value)

    @classmethod
    def from_integer(cls, value: int) -> ModelValidationValue:
        """Create validation value from integer."""
        return cls(value_type=EnumValidationValueType.INTEGER, raw_value=value)

    @classmethod
    def from_boolean(cls, value: bool) -> ModelValidationValue:
        """Create validation value from boolean."""
        return cls(value_type=EnumValidationValueType.BOOLEAN, raw_value=value)

    @classmethod
    def from_null(cls) -> ModelValidationValue:
        """Create validation value for null/None."""
        return cls(value_type=EnumValidationValueType.NULL, raw_value=None)

    @classmethod
    def from_any(cls, value: InputValueType) -> ModelValidationValue:
        """Create validation value from any Python value with automatic type detection."""
        if value is None:
            return cls.from_null()
        if isinstance(value, str):
            return cls.from_string(value)
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.from_boolean(value)
        if isinstance(value, int):
            return cls.from_integer(value)
        # Convert unknown types to string representation
        return cls.from_string(str(value))

    def to_python_value(self) -> ValidationValueType:
        """Convert back to Python native value."""
        return self.raw_value

    def __str__(self) -> str:
        """String representation of the validation value."""
        if self.value_type == EnumValidationValueType.NULL:
            return "null"
        return str(self.raw_value)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelValidationValue"]
