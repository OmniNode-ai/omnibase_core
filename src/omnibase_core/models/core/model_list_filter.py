"""List/collection-based custom filter model."""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_custom_filter_base import ModelCustomFilterBase


class ModelListFilter(ModelCustomFilterBase):
    """List/collection-based custom filter.

    Uses ModelSchemaValue for type-safe list values.
    """

    filter_type: str = Field(default="list", description="Filter type identifier")
    values: list[ModelSchemaValue] = Field(
        default=..., description="List of values to match (type-safe)"
    )
    match_all: bool = Field(default=False, description="Must match all values (vs any)")
    exclude: bool = Field(default=False, description="Exclude matching items")

    @field_validator("values", mode="before")
    @classmethod
    def convert_values_to_schema(cls, v: Any) -> list[ModelSchemaValue]:
        """Convert values to ModelSchemaValue for type safety."""
        if not v:
            return []
        # If already ModelSchemaValue instances, return as-is
        # Note: len(v) > 0 check removed - guaranteed non-empty after early return
        if isinstance(v[0], ModelSchemaValue):
            # First element is ModelSchemaValue, so list is homogeneous ModelSchemaValue list
            return cast(list[ModelSchemaValue], v)
        # Convert raw values to ModelSchemaValue
        return [ModelSchemaValue.from_value(item) for item in v]
