"""
Model Condition Value List - Container for list[Any]of strongly-typed condition values.

list[Any]container for workflow condition values
that maintains type safety and provides utility methods for value checking.

Strict typing is enforced: No string conditions or Any types allowed.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_constraints import PrimitiveValueType


class ModelConditionValueList(BaseModel):
    """Container for list[Any]of strongly-typed condition values."""

    values: list[PrimitiveValueType] = Field(
        default=...,
        description="List of condition values",
    )

    def contains(self, item: PrimitiveValueType) -> bool:
        """Check if the list[Any]contains the specified item."""
        return item in self.values

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
