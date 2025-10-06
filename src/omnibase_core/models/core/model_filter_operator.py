from pydantic import Field

"""
FilterOperator model.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelFilterOperator(BaseModel):
    """Filter operator configuration."""

    operator: str = Field(
        ...,
        description="Operator type (eq/ne/gt/lt/gte/lte/in/nin/like/regex)",
    )
    value: str | int | float | bool | list[Any] = Field(
        ...,
        description="Filter value",
    )
    case_sensitive: bool = Field(
        True,
        description="Case sensitivity for string operations",
    )
