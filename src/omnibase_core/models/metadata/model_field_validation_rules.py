"""
Field validation rules sub-model.

Part of the metadata field info restructuring to reduce string field violations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_numeric_value import ModelNumericValue, NumericInput


class ModelFieldValidationRules(BaseModel):
    """Validation rules for metadata fields."""

    # Validation constraints (non-string where possible)
    validation_pattern: str | None = Field(
        default=None,
        description="Regex pattern for string validation",
    )

    min_length: int | None = Field(
        default=None,
        description="Minimum length for string fields",
    )

    max_length: int | None = Field(
        default=None,
        description="Maximum length for string fields",
    )

    min_value: ModelNumericValue | None = Field(
        default=None,
        description="Minimum value for numeric fields",
    )

    max_value: ModelNumericValue | None = Field(
        default=None,
        description="Maximum value for numeric fields",
    )

    allow_empty: bool = Field(
        default=True,
        description="Whether empty values are allowed",
    )

    def has_string_validation(self) -> bool:
        """Check if string validation rules are defined."""
        return (
            self.validation_pattern is not None
            or self.min_length is not None
            or self.max_length is not None
        )

    def has_numeric_validation(self) -> bool:
        """Check if numeric validation rules are defined."""
        return self.min_value is not None or self.max_value is not None

    def is_valid_string(self, value: str) -> bool:
        """Validate a string value against the rules."""
        if not self.allow_empty and not value:
            return False

        if self.min_length is not None and len(value) < self.min_length:
            return False

        if self.max_length is not None and len(value) > self.max_length:
            return False

        if self.validation_pattern is not None:
            import re

            try:
                return bool(re.match(self.validation_pattern, value))
            except re.error:
                return False

        return True

    def is_valid_numeric(self, value: NumericInput) -> bool:
        """Validate a numeric value against the rules."""
        # Convert to comparable value
        if isinstance(value, ModelNumericValue):
            comparison_value = value.to_python_value()
        else:
            comparison_value = value

        if (
            self.min_value is not None
            and comparison_value < self.min_value.to_python_value()
        ):
            return False

        if (
            self.max_value is not None
            and comparison_value > self.max_value.to_python_value()
        ):
            return False

        return True

    def set_min_value(self, value: NumericInput) -> None:
        """Set minimum value validation rule."""
        if isinstance(value, ModelNumericValue):
            self.min_value = value
        else:
            self.min_value = ModelNumericValue.from_numeric(value)

    def set_max_value(self, value: NumericInput) -> None:
        """Set maximum value validation rule."""
        if isinstance(value, ModelNumericValue):
            self.max_value = value
        else:
            self.max_value = ModelNumericValue.from_numeric(value)

    def get_min_value(self) -> ModelNumericValue | None:
        """Get minimum value as ModelNumericValue."""
        return self.min_value

    def get_max_value(self) -> ModelNumericValue | None:
        """Get maximum value as ModelNumericValue."""
        return self.max_value

    def get_min_value_as_python(self) -> float | None:
        """Get minimum value as Python float for backward compatibility."""
        return self.min_value.to_python_value() if self.min_value else None

    def get_max_value_as_python(self) -> float | None:
        """Get maximum value as Python float for backward compatibility."""
        return self.max_value.to_python_value() if self.max_value else None


# Export the model
__all__ = ["ModelFieldValidationRules"]
