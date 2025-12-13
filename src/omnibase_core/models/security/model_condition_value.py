"""
ModelConditionValue: Strongly typed value for permission conditions.

This model provides strongly typed values for permission conditions without using Any types.
"""

from pydantic import BaseModel, Field


class ModelConditionValue(BaseModel):
    """Strongly typed value for permission conditions."""

    # Only one of these should be set
    string_value: str | None = Field(
        default=None, description="String value for comparison"
    )
    integer_value: int | None = Field(
        default=None,
        description="Integer value for comparison",
    )
    float_value: float | None = Field(
        default=None, description="Float value for comparison"
    )
    boolean_value: bool | None = Field(
        default=None,
        description="Boolean value for comparison",
    )
    list_string_value: list[str] | None = Field(
        default=None,
        description="List of strings for comparison",
    )
    list_integer_value: list[int] | None = Field(
        default=None,
        description="List of integers for comparison",
    )

    # union-ok: condition_value - domain-specific typed lists (list[str], list[int]) not list[Any]
    def get_value(self) -> str | int | float | bool | list[str] | list[int] | None:
        """Get the actual value that is set."""
        if self.string_value is not None:
            return self.string_value
        if self.integer_value is not None:
            return self.integer_value
        if self.float_value is not None:
            return self.float_value
        if self.boolean_value is not None:
            return self.boolean_value
        if self.list_string_value is not None:
            return self.list_string_value
        if self.list_integer_value is not None:
            return self.list_integer_value
        return None
