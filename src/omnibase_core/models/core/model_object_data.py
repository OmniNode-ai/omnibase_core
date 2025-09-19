"""Centralized ModelObjectData implementation."""

from typing import Any

from pydantic import BaseModel, Field

from .model_generic_metadata import ModelGenericMetadata


class ModelObjectData(BaseModel):
    """Generic objectdata model for common use."""

    data: ModelGenericMetadata | None = Field(
        default=None,
        description="Arbitrary object data for flexible field content",
    )
