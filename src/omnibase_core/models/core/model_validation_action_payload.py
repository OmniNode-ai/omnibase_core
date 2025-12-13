"""
Validation Action Payload Model.

Payload for validation actions (validate, verify, check, test).
"""

from pydantic import Field, field_validator

from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType


class ModelValidationActionPayload(ModelActionPayloadBase):
    """Payload for validation actions (validate, verify, check, test)."""

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Validation rules to apply",
    )
    strict_mode: bool = Field(
        default=False,
        description="Whether to use strict validation",
    )
    fail_fast: bool = Field(
        default=False,
        description="Whether to stop on first validation failure",
    )
    include_warnings: bool = Field(
        default=True,
        description="Whether to include warnings in results",
    )

    @field_validator("action_type")
    @classmethod
    def validate_validation_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid validation action."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.core.model_predefined_categories import VALIDATION
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        if v.category != VALIDATION:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid validation action: {v.name}",
            )
        return v
