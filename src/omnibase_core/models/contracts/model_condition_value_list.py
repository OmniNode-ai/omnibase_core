"""
Model Condition Value List - Container for list of strongly-typed condition values.

ONEX Standards Compliant list container for workflow condition values
that maintains type safety and provides utility methods for value checking.

ZERO TOLERANCE: No string conditions or Any types allowed.
"""

from pydantic import BaseModel, Field


class ModelConditionValueList(BaseModel):
    """Container for list of strongly-typed condition values."""

    values: list[str | int | float | bool] = Field(
        ..., description="List of condition values"
    )

    def contains(self, item: str | int | float | bool) -> bool:
        """Check if the list contains the specified item."""
        return item in self.values

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
