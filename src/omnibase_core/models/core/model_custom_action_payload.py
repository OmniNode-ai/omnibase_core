"""
Custom Action Payload Model.

Payload for custom actions that don't fit standard categories.
"""

from typing import Any

from pydantic import Field, field_validator

from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.nodes.model_node_action_type import ModelNodeActionType

from .model_generic_metadata import ModelGenericMetadata


class ModelCustomActionPayload(ModelActionPayloadBase):
    """Payload for custom actions that don't fit standard categories."""

    custom_parameters: ModelGenericMetadata | None = Field(
        None,
        description="Custom parameters for the action",
    )

    @field_validator("action_type")
    @classmethod
    def validate_custom_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid custom action."""
        if v.name != "custom":
            msg = f"Invalid custom action: {v.name}"
            raise ValueError(msg)
        return v
