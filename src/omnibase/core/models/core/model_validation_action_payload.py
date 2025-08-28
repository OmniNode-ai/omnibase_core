"""
Validation Action Payload Model.

Payload for validation actions (validate, verify, check, test).
"""

from typing import List

from pydantic import Field, field_validator

from omnibase.model.core.model_action_payload_base import ModelActionPayloadBase
from omnibase.model.core.model_node_action_type import ModelNodeActionType


class ModelValidationActionPayload(ModelActionPayloadBase):
    """Payload for validation actions (validate, verify, check, test)."""

    validation_rules: List[str] = Field(
        default_factory=list, description="Validation rules to apply"
    )
    strict_mode: bool = Field(
        default=False, description="Whether to use strict validation"
    )
    fail_fast: bool = Field(
        default=False, description="Whether to stop on first validation failure"
    )
    include_warnings: bool = Field(
        default=True, description="Whether to include warnings in results"
    )

    @field_validator("action_type")
    @classmethod
    def validate_validation_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid validation action."""
        from omnibase.model.core.predefined_categories import VALIDATION

        if v.category != VALIDATION:
            raise ValueError(f"Invalid validation action: {v.name}")
        return v
