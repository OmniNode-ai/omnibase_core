"""
EnumLifecycle Action Payload Model.

Payload for lifecycle actions (health_check, initialize, shutdown, etc.).
"""

from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelLifecycleActionPayload(ModelActionPayloadBase):
    """Payload for lifecycle actions (health_check, initialize, shutdown, etc.)."""

    timeout_seconds: int | None = Field(
        default=None,
        description="Timeout for the lifecycle action",
    )
    graceful: bool = Field(
        default=True,
        description="Whether to perform graceful shutdown/restart",
    )

    @field_validator("action_type")
    @classmethod
    def validate_lifecycle_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid lifecycle action."""
        from omnibase_core.models.core.model_predefined_categories import LIFECYCLE

        if v.category != LIFECYCLE:
            msg = f"Invalid lifecycle action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
