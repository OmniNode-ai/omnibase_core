"""
Registry Action Payload Model.

Payload for registry actions (register, unregister, discover).
"""

from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from omnibase_core.model.core.model_action_payload_base import \
    ModelActionPayloadBase
from omnibase_core.model.core.model_node_action_type import ModelNodeActionType


class ModelRegistryActionPayload(ModelActionPayloadBase):
    """Payload for registry actions (register, unregister, discover)."""

    service_name: Optional[str] = Field(
        None, description="Name of the service to register/unregister"
    )
    service_config: Dict[str, Any] = Field(
        default_factory=dict, description="Service configuration"
    )
    discovery_filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filters for service discovery"
    )

    @field_validator("action_type")
    @classmethod
    def validate_registry_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid registry action."""
        if v.name not in ["register", "unregister", "discover"]:
            raise ValueError(f"Invalid registry action: {v.name}")
        return v
