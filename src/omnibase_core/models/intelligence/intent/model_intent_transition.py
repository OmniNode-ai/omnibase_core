# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent graph transition (edge) model.

Represents a directed edge in the Intent Graph — an observed transition between
two intent classes across user sessions. Edges aggregate statistics from all
observed transitions between the same pair of intent classes.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass

__all__ = ["ModelIntentTransition"]


class ModelIntentTransition(BaseModel):
    """Intent graph edge with transition statistics.

    Represents the observed pattern of sessions moving from one intent class
    to another within a single multi-intent session or across sequential
    sessions. Aggregated statistics enable predictive routing and cost modeling.

    Attributes:
        from_intent_class: The source intent class (edge origin).
        to_intent_class: The target intent class (edge destination).
        transition_count: Number of times this transition was observed.
        avg_success_rate: Average success rate for sessions that followed
            this transition, in [0.0, 1.0].
        avg_cost_usd: Average cost in US dollars for sessions that included
            this transition.

    Example:
        >>> from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass
        >>> transition = ModelIntentTransition(
        ...     from_intent_class=EnumIntentClass.ANALYSIS,
        ...     to_intent_class=EnumIntentClass.REFACTOR,
        ...     transition_count=38,
        ...     avg_success_rate=0.87,
        ...     avg_cost_usd=0.034,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    from_intent_class: EnumIntentClass = Field(
        description="The source intent class (edge origin)",
    )
    to_intent_class: EnumIntentClass = Field(
        description="The target intent class (edge destination)",
    )
    transition_count: int = Field(
        ge=0,
        description="Number of times this transition was observed",
    )
    avg_success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Average success rate for sessions that followed this transition, in [0.0, 1.0]"
        ),
    )
    avg_cost_usd: float = Field(
        ge=0.0,
        description=(
            "Average cost in US dollars for sessions that included this transition"
        ),
    )
