"""Centralized ModelObjectData implementation."""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelObjectData(BaseModel):
    """Generic objectdata model for common use."""

    data: SerializedDict | None = Field(
        default_factory=dict,
        description="Arbitrary object data for flexible field content",
    )
