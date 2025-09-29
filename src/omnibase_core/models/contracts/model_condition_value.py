"""
Model Condition Value - Generic container for strongly-typed condition values.

ONEX Standards Compliant typed value container that eliminates Any types
and enforces structured value handling for workflow conditions.

ZERO TOLERANCE: No string conditions or Any types allowed.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Type-safe value types
ConditionValue = TypeVar("ConditionValue", str, int, float, bool)


class ModelConditionValue(BaseModel, Generic[ConditionValue]):
    """Generic container for strongly-typed condition values."""

    value: ConditionValue = Field(..., description="Typed condition value")

    @property
    def python_type(self) -> type:
        """Get the Python type of the contained value."""
        return type(self.value)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
