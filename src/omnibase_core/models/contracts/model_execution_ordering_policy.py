"""
Execution Ordering Policy Model.

Defines how handlers are ordered within execution phases for contract profiles.
This model is used by profile factories to specify ordering behavior.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionOrderingPolicy(BaseModel):
    """
    Defines how handlers are ordered within execution phases.

    Used by contract profiles to specify ordering behavior for handler execution.
    The ordering policy determines how handlers are sorted within each phase.

    Attributes:
        strategy: The ordering strategy to use (currently only topological_sort)
        tie_breakers: List of tie-breaking criteria when ordering is ambiguous
        deterministic_seed: Whether to use a fixed seed for deterministic ordering
    """

    strategy: Literal["topological_sort"] = Field(
        default="topological_sort",
        description="Strategy for ordering handlers within phases",
    )

    tie_breakers: list[Literal["priority", "alphabetical"]] = Field(
        default=["priority", "alphabetical"],
        description="Tie-breaking criteria when ordering is ambiguous",
    )

    deterministic_seed: bool = Field(
        default=True,
        description="Use fixed seed for deterministic ordering across runs",
    )

    strict_mode: bool = Field(
        default=False,
        description=(
            "When True, missing dependency references (handler:X, capability:Y, tag:Z) "
            "are treated as errors instead of warnings, making the execution plan invalid"
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
        from_attributes=True,
    )
