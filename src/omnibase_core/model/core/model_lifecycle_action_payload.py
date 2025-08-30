"""
Lifecycle Action Payload Model.

Payload for lifecycle actions (health_check, initialize, shutdown, etc.).
"""

from typing import Optional

from pydantic import Field, field_validator

from omnibase_core.model.core.model_action_payload_base import \
    ModelActionPayloadBase
from omnibase_core.model.core.model_node_action_type import ModelNodeActionType


class ModelLifecycleActionPayload(ModelActionPayloadBase):
    """Payload for lifecycle actions (health_check, initialize, shutdown, etc.)."""

    timeout_seconds: Optional[int] = Field(
        None, description="Timeout for the lifecycle action"
    )
    graceful: bool = Field(
        default=True, description="Whether to perform graceful shutdown/restart"
    )

    @field_validator("action_type")
    @classmethod
    def validate_lifecycle_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid lifecycle action."""
        from omnibase_core.model.core.predefined_categories import LIFECYCLE

        if v.category != LIFECYCLE:
            raise ValueError(f"Invalid lifecycle action: {v.name}")
        return v
