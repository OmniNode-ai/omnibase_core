"""
Strongly-typed FSM state model.

Replaces dict[str, Any] usage in FSM state operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelFsmState(BaseModel):
    """
    Strongly-typed FSM state.
    """

    name: str = Field(..., description="State name")
    description: str = Field(default="", description="State description")
    is_initial: bool = Field(
        default=False, description="Whether this is the initial state"
    )
    is_final: bool = Field(default=False, description="Whether this is a final state")
    entry_actions: list[str] = Field(
        default_factory=list, description="Actions on state entry"
    )
    exit_actions: list[str] = Field(
        default_factory=list, description="Actions on state exit"
    )
    properties: dict[str, str] = Field(
        default_factory=dict, description="State properties"
    )


# Export for use
__all__ = ["ModelFsmState"]
