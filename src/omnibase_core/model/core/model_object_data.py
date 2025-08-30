"""Centralized ModelObjectData implementation."""

from typing import Any

from pydantic import BaseModel, Field


class ModelObjectData(BaseModel):
    """Generic objectdata model for common use."""

    data: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Arbitrary object data for flexible field content",
    )
