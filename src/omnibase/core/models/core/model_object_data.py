"""Centralized ModelObjectData implementation."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelObjectData(BaseModel):
    """Generic objectdata model for common use."""

    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arbitrary object data for flexible field content",
    )
