"""
Numeric value model.

Type-safe numeric value container that replaces int | float unions
with structured validation and proper type handling.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...enums.enum_numeric_type import EnumNumericType
from ...exceptions.onex_error import OnexError
from ...models.common.model_error_context import ModelErrorContext
from ...models.common.model_schema_value import ModelSchemaValue

# Type alias for numeric input parameters - only accepts structured type for inputs
NumericInput = "ModelNumericValue"


class ModelNumericValue(BaseModel):
    """
    Type-safe numeric value container.

    Replaces int | float unions with structured value storage
    that maintains type information for numeric validation.
    """

    # Value storage with type tracking
    value: float = Field(
        description="The numeric value (stored as float for compatibility)",
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
        None,
        description="Source of the numeric value",
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: Any, info: ValidationInfo) -> float:
        """Validate that value is numeric."""
        if not isinstance(v, (int, float)):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be numeric, got {type(v)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("int or float"),
                        "actual_type": ModelSchemaValue.from_value(str(type(v))),
                        "value": ModelSchemaValue.from_value(str(v)),
                    }
                ),
            )
        return float(v)  # Always store as float for compatibility

    @classmethod
    def from_int(cls, value: int, source: str | None = None) -> ModelNumericValue:
        """Create numeric value from integer."""
        return cls(
            value=float(value),
            value_type=EnumNumericType.INTEGER,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelNumericValue:
        """Create numeric value from float."""
        return cls(
            value=value,
            value_type=EnumNumericType.FLOAT,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_numeric(
        cls, value: int | float, source: str | None = None
    ) -> ModelNumericValue:
        """Create numeric value from int or float."""
        if isinstance(value, int):
            return cls.from_int(value, source)
        elif isinstance(value, float):
            return cls.from_float(value, source)
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be int or float, got {type(value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("int or float"),
                        "actual_type": ModelSchemaValue.from_value(str(type(value))),
                        "value": ModelSchemaValue.from_value(str(value)),
                    }
                ),
            )

    def as_int(self) -> int:
        """Get value as integer."""
        return int(self.value)

    def as_float(self) -> float:
        """Get value as float."""
        return self.value

    def to_python_value(self) -> int | float:
        """Get the underlying Python value with original type."""
        if self.value_type == EnumNumericType.INTEGER:
            return int(self.value)
        return self.value

    def compare_value(self, other: "ModelNumericValue | int | float") -> bool:
        """Compare with another numeric value."""
        if isinstance(other, ModelNumericValue):
            return self.value == other.value
        return self.value == float(other)

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, ModelNumericValue):
            return self.value == other.value
        if isinstance(other, (int, float)):
            return self.value == float(other)
        return False

    def __lt__(self, other: "ModelNumericValue | int | float") -> bool:
        """Less than comparison."""
        if isinstance(other, ModelNumericValue):
            return self.value < other.value
        return self.value < float(other)

    def __le__(self, other: "ModelNumericValue | int | float") -> bool:
        """Less than or equal comparison."""
        if isinstance(other, ModelNumericValue):
            return self.value <= other.value
        return self.value <= float(other)

    def __gt__(self, other: "ModelNumericValue | int | float") -> bool:
        """Greater than comparison."""
        if isinstance(other, ModelNumericValue):
            return self.value > other.value
        return self.value > float(other)

    def __ge__(self, other: "ModelNumericValue | int | float") -> bool:
        """Greater than or equal comparison."""
        if isinstance(other, ModelNumericValue):
            return self.value >= other.value
        return self.value >= float(other)


# Export the model and type alias
__all__ = ["ModelNumericValue", "NumericInput"]
