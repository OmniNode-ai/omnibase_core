"""
Operational Action Payload Model.

Payload for operational actions (process, execute, run, etc.).
"""

from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from omnibase.model.core.model_action_payload_base import ModelActionPayloadBase
from omnibase.model.core.model_node_action_type import ModelNodeActionType


class ModelOperationalActionPayload(ModelActionPayloadBase):
    """Payload for operational actions (process, execute, run, etc.)."""

    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the operation"
    )
    async_execution: bool = Field(
        default=False, description="Whether to execute asynchronously"
    )
    timeout_seconds: Optional[int] = Field(
        None, description="Timeout for the operation"
    )
    retry_count: int = Field(
        default=0, description="Number of retries if operation fails"
    )

    @field_validator("action_type")
    @classmethod
    def validate_operational_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid operational action."""
        from omnibase.model.core.predefined_categories import OPERATION

        if v.category != OPERATION:
            raise ValueError(f"Invalid operational action: {v.name}")
        return v
