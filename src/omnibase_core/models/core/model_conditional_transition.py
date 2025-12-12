"""
Conditional Transition Model.

Transition that applies different updates based on conditions.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.typed_dict_conditional_branch import TypedDictConditionalBranch
from omnibase_core.types.typed_dict_transition_config import TypedDictTransitionConfig


class ModelConditionalTransition(BaseModel):
    """Transition that applies different updates based on conditions."""

    # List of condition/transition pairs with typed structure
    branches: list[TypedDictConditionalBranch] = Field(
        default=...,
        description="List of condition/transition pairs",
    )

    # Transition configuration to apply if no conditions match
    default_transition: TypedDictTransitionConfig | None = Field(
        default=None,
        description="Transition to apply if no conditions match",
    )
