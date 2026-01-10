"""
Execution Profile Model.

Defines execution configuration embedded in contract profiles.
This model specifies phases and ordering policy for handler execution.

See Also:
    - OMN-1227: ProtocolConstraintValidator for SPI
    - OMN-1292: Core Models for ProtocolConstraintValidator

.. versionchanged:: 0.6.0
    Added nondeterministic_allowed_phases field and phase_order property (OMN-1292)
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
        nondeterministic_allowed_phases: Phases where nondeterministic effects are permitted

    See Also:
        - OMN-1227: ProtocolConstraintValidator for SPI
        - OMN-1292: Core Models for ProtocolConstraintValidator

    .. versionchanged:: 0.6.0
        Added nondeterministic_allowed_phases and phase_order property (OMN-1292)
    """

    phases: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXECUTION_PHASES),
        description="Execution phases in order",
    )

    ordering_policy: ModelExecutionOrderingPolicy = Field(
        default_factory=ModelExecutionOrderingPolicy,
        description="Policy for ordering handlers within phases",
    )

    nondeterministic_allowed_phases: list[str] = Field(
        default_factory=list,
        description="Phases where nondeterministic effects are permitted",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
        from_attributes=True,
    )

    @property
    def phase_order(self) -> dict[str, int]:
        """
        Phase -> position mapping derived from phases list.

        Returns:
            Dictionary mapping phase names to their position indices.

        Example:
            >>> profile = ModelExecutionProfile(phases=["init", "execute", "cleanup"])
            >>> profile.phase_order
            {'init': 0, 'execute': 1, 'cleanup': 2}
        """
        return {phase: idx for idx, phase in enumerate(self.phases)}

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        """
        Validate profile invariants.

        Ensures:
        - phases are unique and non-empty strings
        - nondeterministic_allowed_phases is a subset of phases

        Returns:
            The validated profile.

        Raises:
            ValueError: If validation fails.
        """
        # Validate phases are unique
        if len(self.phases) != len(set(self.phases)):
            raise ValueError("phases must contain unique values")

        # Validate phases are non-empty strings
        for phase in self.phases:
            if not phase or not phase.strip():
                raise ValueError("phases must be non-empty strings")

        # Validate nondeterministic_allowed_phases is subset of phases
        phases_set = set(self.phases)
        invalid_phases = set(self.nondeterministic_allowed_phases) - phases_set
        if invalid_phases:
            raise ValueError(
                f"nondeterministic_allowed_phases contains phases not in phases: "
                f"{sorted(invalid_phases)}"
            )

        return self
