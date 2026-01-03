"""
Model for representing ambiguous FSM transitions.

An ambiguous transition occurs when the same trigger from the same source state
can lead to multiple target states at the same priority level.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelAmbiguousTransition(BaseModel):
    """
    Represents an ambiguous transition where the same trigger from the same
    source state can lead to multiple target states.

    This is a semantic error because the FSM executor cannot determine which
    transition to follow when the trigger fires. Even if conditions differ,
    this creates non-deterministic behavior that should be refactored.

    Attributes:
        from_state: Source state name where ambiguity occurs
        trigger: Trigger name that causes the ambiguity
        target_states: Immutable set of possible target states (2+ states means ambiguity)
        priority: Priority level at which the ambiguity occurs
    """

    from_state: str = Field(
        ...,
        description="Source state where the ambiguous transition originates",
        min_length=1,
    )

    trigger: str = Field(
        ...,
        description="Trigger name that leads to multiple possible targets",
        min_length=1,
    )

    target_states: frozenset[str] = Field(
        ...,
        description="Immutable set of possible target states (2+ indicates ambiguity)",
    )

    priority: int = Field(
        ...,
        description="Priority level at which the ambiguity occurs",
    )

    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        extra="forbid",  # No extra fields allowed
        from_attributes=True,  # pytest-xdist compatibility
    )


__all__ = ["ModelAmbiguousTransition"]
