from pydantic import field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Registry Action Payload Model.

Payload for registry actions (register, unregister, discover).
"""

from typing import Any

from pydantic import Field

from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType


class ModelRegistryActionPayload(ModelActionPayloadBase):
    """Payload for registry actions (register, unregister, discover)."""

    service_name: str | None = Field(
        default=None,
        description="Name of the service to register/unregister",
    )
    service_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Service configuration",
    )
    discovery_filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filters for service discovery",
    )

    @field_validator("action_type")
    @classmethod
    def validate_registry_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid registry action."""
        if v.name not in ["register", "unregister", "discover"]:
            msg = f"Invalid registry action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
