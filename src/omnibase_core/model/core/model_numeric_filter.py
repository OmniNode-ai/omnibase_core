"""Numeric range custom filter model."""

from typing import Optional

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelNumericFilter(ModelCustomFilterBase):
    """Numeric range custom filter."""

    filter_type: str = Field(default="numeric", description="Filter type identifier")
    min_value: Optional[float] = Field(None, description="Minimum value (inclusive)")
    max_value: Optional[float] = Field(None, description="Maximum value (inclusive)")
    exact_value: Optional[float] = Field(None, description="Exact value to match")
    tolerance: float = Field(0.0, description="Tolerance for float comparisons")
