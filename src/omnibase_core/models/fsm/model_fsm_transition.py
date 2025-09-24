"""
Strongly-typed FSM transition model.

Replaces dict[str, Any] usage in FSM transition operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelFsmTransition(BaseModel):
    """
    Strongly-typed FSM transition.
    """

    from_state: str = Field(..., description="Source state of transition")
    to_state: str = Field(..., description="Target state of transition")
    trigger: str = Field(..., description="Event that triggers the transition")
    conditions: list[str] = Field(
        default_factory=list, description="Conditions for transition"
    )
    actions: list[str] = Field(
        default_factory=list, description="Actions to execute on transition"
    )


# Export for use
__all__ = ["ModelFsmTransition"]
