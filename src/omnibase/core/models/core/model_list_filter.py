"""List/collection-based custom filter model."""

from typing import Any, List

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelListFilter(ModelCustomFilterBase):
    """List/collection-based custom filter."""

    filter_type: str = Field(default="list", description="Filter type identifier")
    values: List[Any] = Field(..., description="List of values to match")
    match_all: bool = Field(False, description="Must match all values (vs any)")
    exclude: bool = Field(False, description="Exclude matching items")
