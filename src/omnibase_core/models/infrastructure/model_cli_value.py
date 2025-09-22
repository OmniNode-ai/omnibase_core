"""
CLI value object model.

Strongly-typed value object for CLI output data, replacing broad union types
with discriminated union patterns following ONEX strong typing standards.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...exceptions.onex_error import OnexError


class EnumCliValueType(str, Enum):
    """CLI value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DICT = "dict"
    LIST = "list"
    NULL = "null"


class ModelCliValue(BaseModel):
    """
    CLI value object with discriminated union pattern.

    Replaces Union[str, int, float, bool, dict, list, None] with
    a strongly-typed discriminated union following ONEX patterns.
    """

    value_type: EnumCliValueType = Field(description="Type of the CLI value")
    raw_value: Any = Field(description="Raw value data")

    @field_validator("raw_value")
    @classmethod
    def validate_raw_value(cls, v: Any, info: Any) -> Any:
        """Validate raw value matches declared type."""
        if "value_type" not in info.data:
            return v

        value_type = info.data["value_type"]

        if value_type == EnumCliValueType.STRING and not isinstance(v, str):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="String value type must contain str data",
            )
        elif value_type == EnumCliValueType.INTEGER and not isinstance(v, int):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Integer value type must contain int data",
            )
        elif value_type == EnumCliValueType.FLOAT and not isinstance(v, float):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Float value type must contain float data",
            )
        elif value_type == EnumCliValueType.BOOLEAN and not isinstance(v, bool):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean value type must contain bool data",
            )
        elif value_type == EnumCliValueType.DICT and not isinstance(v, dict):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Dict value type must contain dict data",
            )
        elif value_type == EnumCliValueType.LIST and not isinstance(v, list):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="List value type must contain list data",
            )
        elif value_type == EnumCliValueType.NULL and v is not None:
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
    def from_list(cls, value: list[Any]) -> ModelCliValue:
        """Create CLI value from list."""
        return cls(value_type=EnumCliValueType.LIST, raw_value=value)

    @classmethod
    def from_null(cls) -> ModelCliValue:
        """Create CLI value for null/None."""
        return cls(value_type=EnumCliValueType.NULL, raw_value=None)

    @classmethod
    def from_any(cls, value: Any) -> ModelCliValue:
        """Create CLI value from any Python value with automatic type detection."""
        if value is None:
            return cls.from_null()
        elif isinstance(value, str):
            return cls.from_string(value)
        elif isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.from_boolean(value)
        elif isinstance(value, int):
            return cls.from_integer(value)
        elif isinstance(value, float):
            return cls.from_float(value)
        elif isinstance(value, dict):
            return cls(value_type=EnumCliValueType.DICT, raw_value=value)
        elif isinstance(value, list):
            return cls.from_list(value)
        else:
            # Convert unknown types to string representation
            return cls.from_string(str(value))

    def to_python_value(self) -> Any:
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


# Export for use
__all__ = ["ModelCliValue", "EnumCliValueType"]
