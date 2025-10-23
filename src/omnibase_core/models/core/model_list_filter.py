"""List/collection-based custom filter model."""

from typing import Any

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelListFilter(ModelCustomFilterBase):
    """List/collection-based custom filter."""

    filter_type: str = Field(default="list[Any]", description="Filter type identifier")
    values: list[Any] = Field(default=..., description="List of values to match")
    match_all: bool = Field(default=False, description="Must match all values (vs any)")
    exclude: bool = Field(default=False, description="Exclude matching items")
