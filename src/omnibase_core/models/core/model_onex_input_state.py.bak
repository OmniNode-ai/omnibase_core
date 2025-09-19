"""
ONEX input state base model.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_generic_metadata import ModelGenericMetadata


class OnexInputState(BaseModel):
    """
    Base input state model following ONEX canonical patterns.

    Provides common fields for all input state models.
    """

    correlation_id: UUID = Field(
        default_factory=uuid4, description="Unique correlation identifier"
    )
    metadata: ModelGenericMetadata | None = Field(
        default_factory=dict, description="Additional metadata"
    )
    timestamp: float | None = Field(None, description="Optional timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {UUID: str}
