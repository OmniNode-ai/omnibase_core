"""
Execution Profile Model.

Defines execution configuration embedded in contract profiles.
This model specifies phases and ordering policy for handler execution.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)

# Default execution phases following ONEX pipeline convention
DEFAULT_EXECUTION_PHASES: list[str] = [
    "preflight",
    "before",
    "execute",
    "after",
    "emit",
    "finalize",
]


class ModelExecutionProfile(BaseModel):
    """
    Execution configuration embedded in contract profiles.

    Defines the execution phases and ordering policy for handler execution.
    Each profile type (orchestrator_safe, orchestrator_parallel, etc.) includes
    an execution field with this configuration.

    Attributes:
        phases: List of execution phases in order
        ordering_policy: Policy for ordering handlers within phases
    """

    phases: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXECUTION_PHASES),
        description="Execution phases in order",
    )

    ordering_policy: ModelExecutionOrderingPolicy = Field(
        default_factory=ModelExecutionOrderingPolicy,
        description="Policy for ordering handlers within phases",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
        from_attributes=True,
    )
