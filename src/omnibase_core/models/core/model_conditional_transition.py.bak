"""
Conditional Transition Model.

Transition that applies different updates based on conditions.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelConditionalTransition(BaseModel):
    """Transition that applies different updates based on conditions."""

    branches: list[dict[str, Any]] = Field(
        default=...,
        description="List of condition/transition pairs",
    )

    default_transition: dict[str, Any] | None = Field(
        default=None,
        description="Transition to apply if no conditions match",
    )
