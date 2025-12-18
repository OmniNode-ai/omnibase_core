"""
Action Configuration Value Model - Discriminated union and factory functions.

This module provides the discriminator function and factory functions for creating
typed config values. The discriminated union type is a Union of
ModelActionConfigStringValue, ModelActionConfigNumericValue, and
ModelActionConfigBooleanValue.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from pydantic import Discriminator

from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.core.model_action_config_boolean_value import (
    ModelActionConfigBooleanValue,
)
from omnibase_core.models.core.model_action_config_numeric_value import (
    ModelActionConfigNumericValue,
)
from omnibase_core.models.core.model_action_config_string_value import (
    ModelActionConfigStringValue,
)


def get_action_config_discriminator_value(v: object) -> str:
    """Extract discriminator value for action configuration values."""
    if isinstance(v, dict):
        value_type = v.get("value_type", "string")
        return str(value_type)
    return str(getattr(v, "value_type", "string"))


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


def from_value(
    value: object,
) -> (
    ModelActionConfigStringValue
    | ModelActionConfigNumericValue
    | ModelActionConfigBooleanValue
):
    """
    Create action config value from any supported type.

    Args:
        value: Input value (str, int, float, bool, or other types)

    Returns:
        Union of ModelActionConfigStringValue, ModelActionConfigNumericValue,
        or ModelActionConfigBooleanValue with appropriate type discrimination
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
    "ModelActionConfigValueUnion",
    "from_bool",
    "from_float",
    "from_int",
    "from_numeric",
    "from_string",
    "from_value",
    "get_action_config_discriminator_value",
]
