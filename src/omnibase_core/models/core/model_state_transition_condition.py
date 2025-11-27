"""
State Transition Condition Model.

Condition that must be met for a transition to apply.
"""

from pydantic import BaseModel, Field


class ModelStateTransitionCondition(BaseModel):
    """Condition that must be met for a transition to apply."""

    expression: str = Field(
        default=...,
        description="Expression to evaluate (e.g., 'state.count > 10')",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if condition fails",
    )

    required_fields: list[str] | None = Field(
        default=None,
        description="Fields that must exist in state for condition",
    )
