from pydantic import field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Custom Action Payload Model.

Payload for custom actions that don't fit standard categories.
"""

from typing import Any

from pydantic import Field

from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType


class ModelCustomActionPayload(ModelActionPayloadBase):
    """Payload for custom actions that don't fit standard categories."""

    custom_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom parameters for the action",
    )

    @field_validator("action_type")
    @classmethod
    def validate_custom_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid custom action."""
        if v.name != "custom":
            msg = f"Invalid custom action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
