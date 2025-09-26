"""
Node configuration value model.

Type-safe configuration value container that replaces str | int unions
with structured validation and proper type handling for node configurations.
"""

from __future__ import annotations

from typing import Union, cast

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelNodeConfigurationValue(BaseModel):
    """
    Type-safe configuration value container for node capabilities.

    Replaces str | int unions with structured value storage
    that maintains type information for configuration validation.
    """

    # Value storage (one will be set)
    string_value: str | None = Field(None, description="String configuration value")
    numeric_value: ModelNumericValue | None = Field(
        None,
        description="Numeric configuration value",
    )

    # Type indicator
    value_type: str = Field(
        ...,
        description="Type of the configuration value: string or numeric",
    )

    @classmethod
    def from_string(cls, value: str) -> ModelNodeConfigurationValue:
        """Create configuration value from string."""
        return cls(
            string_value=value,
            numeric_value=None,
            value_type="string",
        )

    @classmethod
    def from_int(cls, value: int) -> ModelNodeConfigurationValue:
        """Create configuration value from integer."""
        return cls(
            string_value=None,
            numeric_value=ModelNumericValue.from_int(value),
            value_type="numeric",
        )

    @classmethod
    def from_numeric(cls, value: ModelNumericValue) -> ModelNodeConfigurationValue:
        """Create configuration value from numeric value."""
        # Value is already ModelNumericValue type
        return cls(
            string_value=None,
            numeric_value=value,
            value_type="numeric",
        )

    @classmethod
    def from_value(cls, value: object) -> ModelNodeConfigurationValue:
        """Create configuration value from any supported type.

        Args:
            value: Input value (str, int, float, bool, or other types)

        Returns:
            ModelNodeConfigurationValue with appropriate type discrimination
        """
        if isinstance(value, str):
            return cls.from_string(value)
        if isinstance(value, int):
            return cls.from_int(value)
        if isinstance(value, float):
            return cls.from_numeric(ModelNumericValue.from_float(value))
        # Fallback to string representation for bool and other types
        return cls.from_string(str(value))

    def to_python_value(self) -> Union[str, int, float]:
        """Get the underlying Python value as the original type.

        Returns:
            str for string values, int/float for numeric values
        """
        if self.value_type == "string" and self.string_value is not None:
            return self.string_value
        if self.value_type == "numeric" and self.numeric_value is not None:
            return self.numeric_value.to_python_value()
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid configuration value state: {self.value_type}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "string_value": ModelSchemaValue.from_value(str(self.string_value)),
                    "numeric_value": ModelSchemaValue.from_value(
                        str(self.numeric_value)
                    ),
                }
            ),
        )

    def as_numeric(self) -> Union[int, float]:
        """Get value as numeric type.

        Returns:
            int or float depending on the stored numeric value
        """
        if self.value_type == "numeric" and self.numeric_value is not None:
            return self.numeric_value.to_python_value()
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Configuration value is not numeric",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "method": ModelSchemaValue.from_value("as_numeric"),
                }
            ),
        )

    def as_string(self) -> str:
        """Get configuration value as string."""
        if self.string_value is not None:
            return self.string_value
        if self.numeric_value is not None:
            return str(self.numeric_value.to_python_value())
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="No value set in configuration",
            details=ModelErrorContext.with_context(
                {
                    "method": ModelSchemaValue.from_value("as_string"),
                    "string_value": ModelSchemaValue.from_value(str(self.string_value)),
                    "numeric_value": ModelSchemaValue.from_value(
                        str(self.numeric_value)
                    ),
                }
            ),
        )

    def as_int(self) -> int:
        """Get configuration value as integer (if numeric)."""
        if self.numeric_value is not None:
            return self.numeric_value.as_int()
        if self.string_value is not None:
            try:
                return int(self.string_value)
            except ValueError as e:
                raise OnexError(
                    code=EnumCoreErrorCode.CONVERSION_ERROR,
                    message=f"Cannot convert string '{self.string_value}' to int",
                    details=ModelErrorContext.with_context(
                        {
                            "string_value": ModelSchemaValue.from_value(
                                str(self.string_value)
                            ),
                            "target_type": ModelSchemaValue.from_value("int"),
                            "original_error": ModelSchemaValue.from_value(str(e)),
                        }
                    ),
                ) from e
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="No value set in configuration",
                details=ModelErrorContext.with_context(
                    {
                        "method": ModelSchemaValue.from_value("as_int"),
                        "string_value": ModelSchemaValue.from_value(
                            str(self.string_value)
                        ),
                        "numeric_value": ModelSchemaValue.from_value(
                            str(self.numeric_value)
                        ),
                    }
                ),
            )

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, ModelNodeConfigurationValue):
            return (
                self.string_value == other.string_value
                and self.numeric_value == other.numeric_value
            )
        # Allow comparison with raw values
        try:
            return self.to_python_value() == other
        except (ValueError, TypeError):
            return False

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelNodeConfigurationValue"]
