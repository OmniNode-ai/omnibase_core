"""
Action Configuration Numeric Value Model.

Strongly-typed numeric configuration value for FSM transition actions and similar use cases.
Provides discriminated union support for type-safe action configurations.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_numeric_value import ModelNumericValue


class ModelActionConfigNumericValue(BaseModel):
    """Numeric action configuration value with discriminated union support."""

    value_type: Literal["numeric"] = Field(
        default="numeric",
        description="Type discriminator for numeric values",
    )

    value: ModelNumericValue = Field(
        ...,
        description="Numeric configuration value",
    )

    def to_python_value(self) -> int | float:
        """Get the underlying Python value."""
        return self.value.to_python_value()

    def as_int(self) -> int:
        """Get configuration value as integer."""
        return self.value.as_int()

    def as_float(self) -> float:
        """Get configuration value as float."""
        return self.value.as_float()

    def as_string(self) -> str:
        """Get configuration value as string."""
        return str(self.value.to_python_value())

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelActionConfigNumericValue"]
