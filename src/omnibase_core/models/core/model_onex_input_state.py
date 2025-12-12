"""
ONEX input state base model.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelOnexInputState(BaseModel):
    """
    Base input state model following ONEX canonical patterns.

    Provides common fields for all input state models.
    """

    correlation_id: UUID = Field(
        default_factory=uuid4, description="Unique correlation identifier"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    timestamp: float | None = Field(default=None, description="Optional timestamp")
