"""
Action Configuration Boolean Value Model.

Strongly-typed boolean configuration value for FSM transition actions and similar use cases.
Provides discriminated union support for type-safe action configurations.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelActionConfigBooleanValue(BaseModel):
    """Boolean action configuration value with discriminated union support."""

    value_type: Literal["boolean"] = Field(
        default="boolean",
        description="Type discriminator for boolean values",
    )

    value: bool = Field(
        ...,
        description="Boolean configuration value",
    )

    def to_python_value(self) -> bool:
        """Get the underlying Python value."""
        return self.value

    def as_bool(self) -> bool:
        """Get configuration value as boolean."""
        return self.value

    def as_string(self) -> str:
        """Get configuration value as string."""
        return str(self.value).lower()

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelActionConfigBooleanValue"]
