# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Numeric value model.

Type-safe numeric value container that replaces int | float unions
with structured validation and proper type handling.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
-----------------------------------------------
This module is part of a carefully managed import chain to avoid circular dependencies.
To avoid circular imports with error_codes, we use TYPE_CHECKING for type hints
and runtime imports in validators that need to raise errors.
"""

from collections.abc import Mapping
from math import isfinite
from typing import NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_numeric_type import EnumNumericType


def _raise_numeric_validation_error(
    message: str,
    *,
    raw_value: object,
    raw_value_type: object,
    assignment_field: str | None,
) -> NoReturn:
    """Raise the canonical validation error without widening the import graph."""
    from omnibase_core.errors.model_onex_error import ModelOnexError

    raise ModelOnexError(
        message=message,
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        raw_value=repr(raw_value),
        raw_value_python_type=type(raw_value).__name__,
        raw_value_type=repr(raw_value_type),
        assignment_field=assignment_field,
    )


class ModelNumericValue(BaseModel):
    """
    Type-safe numeric value container.

    Replaces int | float unions with structured value storage
    that maintains type information for numeric validation.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Value storage with type tracking
    value: float = Field(
        description="The numeric value",
    )

    value_type: EnumNumericType = Field(
        description="Type of the numeric value",
    )

    # Validation metadata
    is_validated: bool = Field(
        default=False,
        description="Whether value has been validated",
    )

    source: str | None = Field(
        default=None,
        description="Source of the numeric value",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_numeric_contract(cls, data: object, info: ValidationInfo) -> object:
        """
        Validate raw numeric value and discriminator before Pydantic coercion.

        The complete candidate mapping is also supplied during assignment validation,
        so invalid value changes and discriminator retags fail before object mutation.
        """
        if not isinstance(data, Mapping):
            return data
        if "value" not in data or "value_type" not in data:
            return data

        raw_value = data["value"]
        raw_value_type = data["value_type"]
        assignment_field = info.field_name

        if isinstance(raw_value_type, EnumNumericType):
            numeric_type = raw_value_type
        elif isinstance(raw_value_type, str):
            if raw_value_type == EnumNumericType.INTEGER.value:
                numeric_type = EnumNumericType.INTEGER
            elif raw_value_type == EnumNumericType.FLOAT.value:
                numeric_type = EnumNumericType.FLOAT
            elif raw_value_type == EnumNumericType.NUMERIC.value:
                numeric_type = EnumNumericType.NUMERIC
            else:
                _raise_numeric_validation_error(
                    "Unsupported numeric value discriminator",
                    raw_value=raw_value,
                    raw_value_type=raw_value_type,
                    assignment_field=assignment_field,
                )
        else:
            _raise_numeric_validation_error(
                "Numeric value discriminator must be an EnumNumericType or canonical string",
                raw_value=raw_value,
                raw_value_type=raw_value_type,
                assignment_field=assignment_field,
            )

        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            _raise_numeric_validation_error(
                "Numeric value must be an int or float; coercion is not permitted",
                raw_value=raw_value,
                raw_value_type=raw_value_type,
                assignment_field=assignment_field,
            )

        if isinstance(raw_value, int):
            try:
                canonical_value = float(raw_value)
            except OverflowError:
                _raise_numeric_validation_error(
                    "Integer value cannot be represented by canonical float storage",
                    raw_value=raw_value,
                    raw_value_type=raw_value_type,
                    assignment_field=assignment_field,
                )
            if not isfinite(canonical_value) or int(canonical_value) != raw_value:
                _raise_numeric_validation_error(
                    "Integer value cannot be represented exactly by canonical float storage",
                    raw_value=raw_value,
                    raw_value_type=raw_value_type,
                    assignment_field=assignment_field,
                )
        elif not isfinite(raw_value):
            _raise_numeric_validation_error(
                "Numeric value must be finite",
                raw_value=raw_value,
                raw_value_type=raw_value_type,
                assignment_field=assignment_field,
            )

        if numeric_type is EnumNumericType.INTEGER:
            if isinstance(raw_value, float) and not raw_value.is_integer():
                _raise_numeric_validation_error(
                    "INTEGER values must be integral and cannot be truncated",
                    raw_value=raw_value,
                    raw_value_type=raw_value_type,
                    assignment_field=assignment_field,
                )
        elif numeric_type is EnumNumericType.FLOAT and not isinstance(raw_value, float):
            _raise_numeric_validation_error(
                "FLOAT values require an explicit float and cannot coerce integers",
                raw_value=raw_value,
                raw_value_type=raw_value_type,
                assignment_field=assignment_field,
            )

        return data

    @classmethod
    def from_int(cls, value: int, source: str | None = None) -> "ModelNumericValue":
        """Create numeric value from integer."""
        return cls(
            value=value,
            value_type=EnumNumericType.INTEGER,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> "ModelNumericValue":
        """Create numeric value from float."""
        return cls(
            value=value,
            value_type=EnumNumericType.FLOAT,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_numeric(
        cls,
        value: int | float,
        source: str | None = None,
    ) -> "ModelNumericValue":
        """Create numeric value from int or float, preserving original type."""
        # Detect the original type and use appropriate method
        if isinstance(value, int):
            return cls.from_int(value, source)
        return cls.from_float(value, source)

    def as_int(self) -> int:
        """Get value as integer."""
        return int(self.value)

    def as_float(self) -> float:
        """Get value as float."""
        return self.value

    @property
    def integer_value(self) -> int:
        """Get value as integer (property access)."""
        return int(self.value)

    @property
    def float_value(self) -> float:
        """Get value as float (property access)."""
        return self.value

    def to_python_value(self) -> int | float:
        """Get the underlying Python value preserving original type."""
        if self.value_type == EnumNumericType.INTEGER:
            return int(self.value)
        return self.value

    def to_original_type(self) -> float:
        """Get the value respecting the original type flag."""
        if self.value_type == EnumNumericType.INTEGER:
            return float(
                int(self.value),
            )  # Ensure integer precision but return as float
        return self.value

    def compare_value(self, other: "ModelNumericValue") -> bool:
        """Compare with another numeric value."""
        return self.value == other.value

    def compare_with_float(self, other: float) -> bool:
        """Compare with a float value."""
        return self.value == other

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, ModelNumericValue):
            return self.value == other.value
        if isinstance(other, (int, float)):
            return self.value == float(other)
        return False

    def __lt__(self, other: "ModelNumericValue") -> bool:
        """Less than comparison."""
        return self.value < other.value

    def __le__(self, other: "ModelNumericValue") -> bool:
        """Less than or equal comparison."""
        return self.value <= other.value

    def __gt__(self, other: "ModelNumericValue") -> bool:
        """Greater than comparison."""
        return self.value > other.value

    def __ge__(self, other: "ModelNumericValue") -> bool:
        """Greater than or equal comparison."""
        return self.value >= other.value

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Note: Previously had type alias (NumericInput = ModelNumericValue)
    # Removed to comply with ONEX strong typing standards.
    # Use explicit type: ModelNumericValue

    # Protocol method implementations

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(mode="json", exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Note: This is a pure validation method that does NOT throw exceptions
        to avoid circular dependencies. Use validation layer for exception-based validation.

        Returns:
            bool: True if validation passes, False otherwise
        """
        # Basic validation - Pydantic already ensures value and value_type are set
        # This method always returns True for properly constructed instances
        return True


__all__ = ["ModelNumericValue"]
