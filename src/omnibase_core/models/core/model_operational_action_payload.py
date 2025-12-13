"""
Operational Action Payload Model.

Payload for operational actions (process, execute, run, etc.).
"""

from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelOperationalActionPayload(ModelActionPayloadBase):
    """Payload for operational actions (process, execute, run, etc.)."""

    parameters: SerializedDict = Field(
        default_factory=dict,
        description="Parameters for the operation",
    )
    async_execution: bool = Field(
        default=False,
        description="Whether to execute asynchronously",
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Timeout for the operation",
    )
    retry_count: int = Field(
        default=0,
        description="Number of retries if operation fails",
    )

    @field_validator("action_type")
    @classmethod
    def validate_operational_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid operational action."""
        from omnibase_core.models.core.model_predefined_categories import OPERATION

        if v.category != OPERATION:
            msg = f"Invalid operational action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
