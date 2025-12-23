"""Effect Result List Model.

List result for effect operations.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelEffectResultList(BaseModel):
    """List result for effect operations.

    Uses ModelSchemaValue for type-safe list values.
    """

    result_type: Literal["list"] = Field(
        default="list", description="Result type identifier"
    )
    value: list[ModelSchemaValue] = Field(
        default=..., description="List of effect result values (type-safe)"
    )

    @field_validator("value", mode="before")
    @classmethod
    def convert_value_to_schema(
        cls, v: list[Any] | list[ModelSchemaValue]
    ) -> list[ModelSchemaValue]:
        """Convert values to ModelSchemaValue for type safety."""
        if not v:
            return []
        # If already ModelSchemaValue instances, return as-is
        if v and isinstance(v[0], ModelSchemaValue):
            return v  # type: ignore[return-value]
        # Convert raw values to ModelSchemaValue
        return [ModelSchemaValue.from_value(item) for item in v]
