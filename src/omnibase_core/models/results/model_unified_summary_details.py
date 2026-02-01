from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelUnifiedSummaryDetails(BaseModel):
    """
    Define canonical fields for summary details, extend as needed.

    Uses ModelSchemaValue for strongly-typed, discriminated union values.
    No automatic conversion - callers must provide ModelSchemaValue instances.
    """

    key: str | None = Field(None, description="Detail key identifier")
    value: ModelSchemaValue | None = Field(
        None, description="Strongly-typed detail value"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
