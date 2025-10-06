from typing import Any, List

from pydantic import Field

"""
Model Condition Value List - Container for list[Any]of strongly-typed condition values.

ONEX Standards Compliant list[Any]container for workflow condition values
that maintains type safety and provides utility methods for value checking.

ZERO TOLERANCE: No string conditions or Any types allowed.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.constraints import PrimitiveValueType


class ModelConditionValueList(BaseModel):
    """Container for list[Any]of strongly-typed condition values."""

    values: list[PrimitiveValueType] = Field(
        default=...,
        description="List of condition values",
    )

    def contains(self, item: PrimitiveValueType) -> bool:
        """Check if the list[Any]contains the specified item."""
        return item in self.values

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
