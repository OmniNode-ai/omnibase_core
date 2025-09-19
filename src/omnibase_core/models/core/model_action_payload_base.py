"""
Action Payload Base Model.

Base class for action-specific payload types with common fields and validation.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata
from omnibase_core.models.nodes.model_node_action_type import ModelNodeActionType


class ModelActionPayloadBase(BaseModel):
    """
    Base class for action-specific payload types.

    Provides common fields and validation for all action payload types.
    """

    action_type: ModelNodeActionType = Field(
        ...,
        description="The rich action type being performed",
    )
    correlation_id: UUID | None = Field(
        None,
        description="Correlation ID for tracking this action",
    )
    metadata: ModelGenericMetadata = Field(
        default_factory=lambda: ModelGenericMetadata(
            created_at=None,
            updated_at=None,
            created_by=None,
            updated_by=None,
            version=None,
            tags=None,
            labels=None,
            annotations=None,
            custom_fields=None,
            extended_data=None,
        ),
        description="Additional metadata for the action",
    )

    model_config = ConfigDict(use_enum_values=True)
