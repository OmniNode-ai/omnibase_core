"""
ModelConditionValue: Strongly typed value for permission conditions.

This model provides strongly typed values for permission conditions without using Any types.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelConditionValue(BaseModel):
    """Strongly typed value for permission conditions."""

    # Only one of these should be set
    string_value: Optional[str] = Field(None, description="String value for comparison")
    integer_value: Optional[int] = Field(
        None, description="Integer value for comparison"
    )
    float_value: Optional[float] = Field(None, description="Float value for comparison")
    boolean_value: Optional[bool] = Field(
        None, description="Boolean value for comparison"
    )
    list_string_value: Optional[List[str]] = Field(
        None, description="List of strings for comparison"
    )
    list_integer_value: Optional[List[int]] = Field(
        None, description="List of integers for comparison"
    )

    def get_value(self):
        """Get the actual value that is set."""
        if self.string_value is not None:
            return self.string_value
        elif self.integer_value is not None:
            return self.integer_value
        elif self.float_value is not None:
            return self.float_value
        elif self.boolean_value is not None:
            return self.boolean_value
        elif self.list_string_value is not None:
            return self.list_string_value
        elif self.list_integer_value is not None:
            return self.list_integer_value
        else:
            return None
