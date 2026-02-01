"""Requirement model for ticket specification."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRequirement(BaseModel):
    """A requirement for the ticket specification.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    id: str = Field(..., description="Unique identifier for the requirement")
    statement: str = Field(..., description="The requirement statement")
    rationale: str | None = Field(
        default=None, description="Reasoning behind the requirement"
    )
    acceptance: list[str] = Field(
        default_factory=list, description="Acceptance criteria for the requirement"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


# Alias for cleaner imports
Requirement = ModelRequirement

__all__ = [
    "ModelRequirement",
    "Requirement",
]
