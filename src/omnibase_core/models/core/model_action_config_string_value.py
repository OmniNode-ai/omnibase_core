"""
Action Configuration String Value Model.

Strongly-typed string configuration value for FSM transition actions and similar use cases.
Provides discriminated union support for type-safe action configurations.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelActionConfigStringValue(BaseModel):
    """String action configuration value with discriminated union support."""

    value_type: Literal["string"] = Field(
        default="string",
        description="Type discriminator for string values",
    )

    value: str = Field(
        ...,
        description="String configuration value",
    )

    def to_python_value(self) -> str:
        """Get the underlying Python value."""
        return self.value

    def as_string(self) -> str:
        """Get configuration value as string."""
        return self.value

    def as_int(self) -> int:
        """Get configuration value as integer (convert from string)."""
        try:
            return int(self.value)
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot convert string '{self.value}' to int",
                details={"value": self.value, "target_type": "int"},
                cause=e,
            ) from e

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelActionConfigStringValue"]
