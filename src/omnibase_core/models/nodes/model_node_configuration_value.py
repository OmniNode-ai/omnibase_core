from __future__ import annotations

from typing import Literal, Union

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Node configuration value model.

Type-safe configuration value container using Pydantic discriminated unions
for proper type safety and validation of node configurations.
"""


from typing import Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_numeric_value import ModelNumericValue

from .model_nodeconfigurationnumericvalue import ModelNodeConfigurationNumericValue


class ModelNodeConfigurationStringValue(BaseModel):
    """String configuration value with discriminated union support."""

    value_type: Literal["string"] = Field(
        default="string",
        description="Type discriminator for string values",
    )
    value: str = Field(default=..., description="String configuration value")

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
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot convert string '{self.value}' to int",
                details={"value": self.value, "target_type": "int"},
                cause=e,
            ) from e


def get_discriminator_value(v: Any) -> str:
    """Extract discriminator value for configuration values."""
    if isinstance(v, dict):
        value_type = v.get("value_type", "string")
        return str(value_type)  # Ensure string type
    return str(getattr(v, "value_type", "string"))  # Ensure string type


# Discriminated union type for configuration values
ModelNodeConfigurationValue = Union[
    ModelNodeConfigurationStringValue,
    ModelNodeConfigurationNumericValue,
]


# Type alias with discriminator annotation for proper Pydantic support
ModelNodeConfigurationValueUnion = Discriminator(
    get_discriminator_value,
    custom_error_type="value_discriminator",
    custom_error_message="Invalid configuration value type",
    custom_error_context={"discriminator": "value_type"},
)


# Factory functions for creating discriminated union instances
def from_string(value: str) -> ModelNodeConfigurationStringValue:
    """Create configuration value from string."""
    return ModelNodeConfigurationStringValue(value=value)


def from_int(value: int) -> ModelNodeConfigurationNumericValue:
    """Create configuration value from integer."""
    return ModelNodeConfigurationNumericValue(value=ModelNumericValue.from_int(value))


def from_float(value: float) -> ModelNodeConfigurationNumericValue:
    """Create configuration value from float."""
    return ModelNodeConfigurationNumericValue(value=ModelNumericValue.from_float(value))


def from_numeric(value: ModelNumericValue) -> ModelNodeConfigurationNumericValue:
    """Create configuration value from numeric value."""
    return ModelNodeConfigurationNumericValue(value=value)


def from_value(value: object) -> ModelNodeConfigurationValue:
    """Create configuration value from any supported type.

    Args:
        value: Input value (str, int, float, bool, or other types)

    Returns:
        ModelNodeConfigurationValue with appropriate type discrimination
    """
    if isinstance(value, str):
        return from_string(value)
    if isinstance(value, int):
        return from_int(value)
    if isinstance(value, float):
        return from_float(value)
    # Fallback to string representation for bool and other types
    return from_string(str(value))


__all__ = [
    "ModelNodeConfigurationNumericValue",
    "ModelNodeConfigurationStringValue",
    "ModelNodeConfigurationValue",
    "ModelNodeConfigurationValueUnion",
    "from_float",
    "from_int",
    "from_numeric",
    "from_string",
    "from_value",
]
