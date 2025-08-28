"""
Data Action Payload Model.

Payload for data actions (read, write, create, update, delete, etc.).
"""

from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from omnibase.model.core.model_action_payload_base import ModelActionPayloadBase
from omnibase.model.core.model_node_action_type import ModelNodeActionType


class ModelDataActionPayload(ModelActionPayloadBase):
    """Payload for data actions (read, write, create, update, delete, etc.)."""

    target_path: Optional[str] = Field(None, description="Path to the data target")
    data: Optional[Dict[str, Any]] = Field(None, description="Data to be processed")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filters for data operations"
    )
    limit: Optional[int] = Field(None, description="Limit for list/search operations")
    offset: Optional[int] = Field(None, description="Offset for pagination")

    @field_validator("action_type")
    @classmethod
    def validate_data_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid data action."""
        from omnibase.model.core.predefined_categories import OPERATION, QUERY

        if v.category not in [OPERATION, QUERY]:
            raise ValueError(f"Invalid data action: {v.name}")
        return v
