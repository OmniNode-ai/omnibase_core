from pydantic import field_validator

from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Management Action Payload Model.

Payload for management actions (configure, deploy, migrate, etc.).
"""

from typing import Any

from pydantic import Field, field_validator

from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType


class ModelManagementActionPayload(ModelActionPayloadBase):
    """Payload for management actions (configure, deploy, migrate, etc.)."""

    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration parameters",
    )
    environment: str | None = Field(
        default=None,
        description="Target environment for deployment",
    )
    force: bool = Field(default=False, description="Force the management action")
    dry_run: bool = Field(
        default=False,
        description="Perform a dry run without making changes",
    )

    @field_validator("action_type")
    @classmethod
    def validate_management_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid management action."""
        from omnibase_core.models.core.model_predefined_categories import MANAGEMENT

        if v.category != MANAGEMENT:
            msg = f"Invalid management action: {v.name}"
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
