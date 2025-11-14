from pydantic import field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Data Action Payload Model.

Payload for data actions (read, write, create, update, delete, etc.).
"""

from typing import Any

from pydantic import Field

from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType


class ModelDataActionPayload(ModelActionPayloadBase):
    """Payload for data actions (read, write, create, update, delete, etc.)."""

    target_path: str | None = Field(default=None, description="Path to the data target")
    data: dict[str, Any] | None = Field(
        default=None, description="Data to be processed"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filters for data operations",
    )
    limit: int | None = Field(
        default=None, description="Limit for list[Any]/search operations"
    )
    offset: int | None = Field(default=None, description="Offset for pagination")

    @field_validator("action_type")
    @classmethod
    def validate_data_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid data action."""
        from omnibase_core.models.core.model_predefined_categories import (
            OPERATION,
            QUERY,
        )

        if v.category not in [OPERATION, QUERY]:
            msg = f"Invalid data action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
