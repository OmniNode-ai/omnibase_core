"""
Custom Action Payload Model.

Payload for custom actions that don't fit standard categories.
"""

from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_custom_parameters import ModelCustomParameters
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelCustomActionPayload(ModelActionPayloadBase):
    """Payload for custom actions that don't fit standard categories."""

    custom_parameters: ModelCustomParameters = Field(
        default_factory=ModelCustomParameters,
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
