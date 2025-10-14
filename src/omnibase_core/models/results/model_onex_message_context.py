from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelOnexMessageContext(BaseModel):
    """
    Define canonical fields for message context, extend as needed.

    Uses ModelSchemaValue for strongly-typed, discriminated union values.
    Automatically converts raw values to ModelSchemaValue.
    """

    key: str | None = Field(None, description="Context key identifier")
    value: ModelSchemaValue | None = Field(
        None, description="Strongly-typed context value"
    )

    @field_validator("value", mode="before")
    @classmethod
    def convert_to_schema_value(cls, v: Any) -> ModelSchemaValue | None:
        """Automatically convert raw values to ModelSchemaValue."""
        if v is None or isinstance(v, ModelSchemaValue):
            return v
        return ModelSchemaValue.from_value(v)

    model_config = {"arbitrary_types_allowed": True}
