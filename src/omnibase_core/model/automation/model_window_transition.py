"""
Model for window transition.

Represents a transition between operational windows.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.automation.model_transition_statistics import (
    ModelTransitionStatistics,
)


class ModelWindowTransition(BaseModel):
    """Represents a transition between operational windows."""

    from_window: str | None = Field(None, description="Previous window ID")
    to_window: str = Field(..., description="New window ID")
    transition_time: datetime = Field(..., description="Time of transition")

    agents_to_stop: list[str] = Field(
        default_factory=list,
        description="Agents to stop during transition",
    )
    agents_to_start: list[str] = Field(
        default_factory=list,
        description="Agents to start in new window",
    )
    agents_to_continue: list[str] = Field(
        default_factory=list,
        description="Agents continuing across windows",
    )

    completed: bool = Field(False, description="Whether transition is complete")
    success: bool = Field(False, description="Whether transition was successful")
    error_message: str | None = Field(None, description="Error if transition failed")

    statistics: ModelTransitionStatistics | None = Field(
        default=None,
        description="Transition performance statistics",
    )
