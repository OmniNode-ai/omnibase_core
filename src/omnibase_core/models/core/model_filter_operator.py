"""
FilterOperator model.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelFilterOperator(BaseModel):
    """Filter operator configuration."""

    operator: str = Field(
        default=...,
        description="Operator type (eq/ne/gt/lt/gte/lte/in/nin/like/regex)",
    )
    value: str | int | float | bool | list[Any] = Field(
        default=...,
        description="Filter value",
    )
    case_sensitive: bool = Field(
        default=True,
        description="Case sensitivity for string operations",
    )
