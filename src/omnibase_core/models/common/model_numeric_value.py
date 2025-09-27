"""
Numeric value model.

Type-safe numeric value container that replaces int | float unions
with structured validation and proper type handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_numeric_type import EnumNumericType

# Import all dependencies only when needed to break circular imports
if TYPE_CHECKING:
    from omnibase_core.exceptions.onex_error import OnexError
    from omnibase_core.models.common.model_error_context import ModelErrorContext
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Forward reference for type alias - will be properly defined after the class


class ModelNumericValue(BaseModel):
    """
    Type-safe numeric value container.

    Replaces int | float unions with structured value storage
    that maintains type information for numeric validation.
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
        None,
        description="Source of the numeric value",
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: object, info: ValidationInfo) -> float:
        """Validate that value is numeric."""
        if not isinstance(v, (int, float)):
            # Use delayed imports to break circular dependencies
            from omnibase_core.exceptions.onex_error import OnexError
            from omnibase_core.models.common.model_error_context import (
                ModelErrorContext,
            )
            from omnibase_core.models.common.model_schema_value import ModelSchemaValue

            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be numeric, got {type(v)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("int or float"),
                        "actual_type": ModelSchemaValue.from_value(str(type(v))),
                        "value": ModelSchemaValue.from_value(str(v)),
                    },
                ),
            )
        return float(v)

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
        cls,
        value: int | float,
        source: str | None = None,
    ) -> ModelNumericValue:
        """Create numeric value from int or float, preserving original type."""
        # Detect the original type and use appropriate method
        if isinstance(value, int):
            return cls.from_int(value, source)
        else:
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
                int(self.value)
            )  # Ensure integer precision but return as float
        return self.value

    def compare_value(self, other: ModelNumericValue) -> bool:
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

    def __lt__(self, other: ModelNumericValue) -> bool:
        """Less than comparison."""
        return self.value < other.value

    def __le__(self, other: ModelNumericValue) -> bool:
        """Less than or equal comparison."""
        return self.value <= other.value

    def __gt__(self, other: ModelNumericValue) -> bool:
        """Greater than comparison."""
        return self.value > other.value

    def __ge__(self, other: ModelNumericValue) -> bool:
        """Greater than or equal comparison."""
        return self.value >= other.value

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Note: Previously had type alias (NumericInput = ModelNumericValue)
# Removed to comply with ONEX strong typing standards.
# Use explicit type: ModelNumericValue

# Export the model and type alias
__all__ = ["ModelNumericValue"]
