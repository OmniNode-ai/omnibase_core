"""
Action Configuration Value Model - ONEX Standards Compliant.

Strongly-typed configuration value for FSM transition actions and similar use cases.
Provides discriminated union support for type-safe action configurations.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


def get_action_config_discriminator_value(v: Any) -> str:
    """Extract discriminator value for action configuration values."""
    if isinstance(v, dict):
        value_type = v.get("value_type", "string")
        return str(value_type)
    return str(getattr(v, "value_type", "string"))


# Discriminated union type for action configuration values
ModelActionConfigValue = Union[
    ModelActionConfigStringValue,
    ModelActionConfigNumericValue,
    ModelActionConfigBooleanValue,
]


# Type alias with discriminator annotation for proper Pydantic support
ModelActionConfigValueUnion = Discriminator(
    get_action_config_discriminator_value,
    custom_error_type="value_discriminator",
    custom_error_message="Invalid action configuration value type",
    custom_error_context={"discriminator": "value_type"},
)


# Factory functions for creating discriminated union instances
def from_string(value: str) -> ModelActionConfigStringValue:
    """Create action config value from string."""
    return ModelActionConfigStringValue(value=value)


def from_int(value: int) -> ModelActionConfigNumericValue:
    """Create action config value from integer."""
    return ModelActionConfigNumericValue(value=ModelNumericValue.from_int(value))


def from_float(value: float) -> ModelActionConfigNumericValue:
    """Create action config value from float."""
    return ModelActionConfigNumericValue(value=ModelNumericValue.from_float(value))


def from_bool(value: bool) -> ModelActionConfigBooleanValue:
    """Create action config value from boolean."""
    return ModelActionConfigBooleanValue(value=value)


def from_numeric(value: ModelNumericValue) -> ModelActionConfigNumericValue:
    """Create action config value from numeric value."""
    return ModelActionConfigNumericValue(value=value)


def from_value(value: object) -> ModelActionConfigValue:
    """
    Create action config value from any supported type.

    Args:
        value: Input value (str, int, float, bool, or other types)

    Returns:
        ModelActionConfigValue with appropriate type discrimination
    """
    if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
        return from_bool(value)
    if isinstance(value, str):
        return from_string(value)
    if isinstance(value, int):
        return from_int(value)
    if isinstance(value, float):
        return from_float(value)
    # Fallback to string representation for other types
    return from_string(str(value))


__all__ = [
    "ModelActionConfigBooleanValue",
    "ModelActionConfigNumericValue",
    "ModelActionConfigStringValue",
    "ModelActionConfigValue",
    "ModelActionConfigValueUnion",
    "from_bool",
    "from_float",
    "from_int",
    "from_numeric",
    "from_string",
    "from_value",
    "get_action_config_discriminator_value",
]
