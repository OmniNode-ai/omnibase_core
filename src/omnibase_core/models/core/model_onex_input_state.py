"""
ONEX input state base model.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.metadata.model_generic_metadata import ModelGenericMetadata


class ModelOnexInputState(BaseModel):
    """
    Base input state model following ONEX canonical patterns.

    Provides common fields for all input state models.
    """

    correlation_id: UUID = Field(
        default_factory=uuid4, description="Unique correlation identifier"
    )
    metadata: ModelGenericMetadata = Field(
        default_factory=ModelGenericMetadata, description="Additional metadata"
    )
    timestamp: float | None = Field(default=None, description="Optional timestamp")
