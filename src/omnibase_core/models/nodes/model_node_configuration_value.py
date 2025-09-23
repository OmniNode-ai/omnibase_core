"""
Node configuration value model.

Type-safe configuration value container that replaces str | int unions
with structured validation and proper type handling for node configurations.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field

from omnibase_core.models.metadata.model_numeric_value import ModelNumericValue


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
    def from_value(cls, value: Any) -> ModelNodeConfigurationValue:
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

    def to_python_value(self) -> Any:
        """Get the underlying Python value as the original type.

        Returns:
            str for string values, int/float for numeric values
        """
        if self.value_type == "string" and self.string_value is not None:
            return self.string_value
        if self.value_type == "numeric" and self.numeric_value is not None:
            return self.numeric_value.to_python_value()
        raise ValueError(f"Invalid configuration value state: {self.value_type}")

    def as_numeric(self) -> Any:
        """Get value as numeric type.

        Returns:
            int or float depending on the stored numeric value
        """
        if self.value_type == "numeric" and self.numeric_value is not None:
            return self.numeric_value.to_python_value()
        raise ValueError("Configuration value is not numeric")

    def as_string(self) -> str:
        """Get configuration value as string."""
        if self.string_value is not None:
            return self.string_value
        if self.numeric_value is not None:
            return str(self.numeric_value.to_python_value())
        raise ValueError("No value set in configuration")

    def as_int(self) -> int:
        """Get configuration value as integer (if numeric)."""
        if self.numeric_value is not None:
            return self.numeric_value.as_int()
        if self.string_value is not None:
            try:
                return int(self.string_value)
            except ValueError as e:
                raise ValueError(
                    f"Cannot convert string '{self.string_value}' to int",
                ) from e
        else:
            raise ValueError("No value set in configuration")

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, ModelNodeConfigurationValue):
            return (
                self.string_value == other.string_value
                and self.numeric_value == other.numeric_value
            )
        # Allow comparison with raw values
        try:
            return cast(bool, self.to_python_value() == other)
        except (ValueError, TypeError):
            return False


# Export the model
__all__ = ["ModelNodeConfigurationValue"]
