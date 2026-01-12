from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelOnexMessageContext(BaseModel):
    """
    Define canonical fields for message context, extend as needed.

    Uses ModelSchemaValue for strongly-typed, discriminated union values.
    No automatic conversion - callers must provide ModelSchemaValue instances.
    """

    key: str | None = Field(None, description="Context key identifier")
    value: ModelSchemaValue | None = Field(
        None, description="Strongly-typed context value"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
