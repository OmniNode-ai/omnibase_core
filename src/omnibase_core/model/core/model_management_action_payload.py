"""
Management Action Payload Model.

Payload for management actions (configure, deploy, migrate, etc.).
"""

from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from omnibase_core.model.core.model_action_payload_base import \
    ModelActionPayloadBase
from omnibase_core.model.core.model_node_action_type import ModelNodeActionType


class ModelManagementActionPayload(ModelActionPayloadBase):
    """Payload for management actions (configure, deploy, migrate, etc.)."""

    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters"
    )
    environment: Optional[str] = Field(
        None, description="Target environment for deployment"
    )
    force: bool = Field(default=False, description="Force the management action")
    dry_run: bool = Field(
        default=False, description="Perform a dry run without making changes"
    )

    @field_validator("action_type")
    @classmethod
    def validate_management_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid management action."""
        from omnibase_core.model.core.predefined_categories import MANAGEMENT

        if v.category != MANAGEMENT:
            raise ValueError(f"Invalid management action: {v.name}")
        return v
