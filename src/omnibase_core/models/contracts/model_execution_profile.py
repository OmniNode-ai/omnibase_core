"""
Execution Profile Model.

Defines execution configuration embedded in contract profiles.
This model specifies phases and ordering policy for handler execution.

The model is fully immutable - all collection fields use tuples rather than
lists to ensure true immutability even though Pydantic's frozen=True only
prevents attribute reassignment but not mutation of mutable contents.

See Also:
    - OMN-1227: ProtocolConstraintValidator for SPI
    - OMN-1292: Core Models for ProtocolConstraintValidator

.. versionchanged:: 0.6.0
    Added nondeterministic_allowed_phases field and phase_order property (OMN-1292)

.. versionchanged:: 0.6.1
    Converted list fields to tuples for true immutability.
    Added cached phase_order property for performance.
    Enhanced validation for nondeterministic_allowed_phases (OMN-1292)
"""

from functools import cached_property
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)

# Default execution phases following ONEX pipeline convention
# Using tuple for immutability
DEFAULT_EXECUTION_PHASES: tuple[str, ...] = (
    "preflight",
    "before",
    "execute",
    "after",
    "emit",
    "finalize",
)


class ModelExecutionProfile(BaseModel):
    """
    Execution configuration embedded in contract profiles.

    Defines the execution phases and ordering policy for handler execution.
    Each profile type (orchestrator_safe, orchestrator_parallel, etc.) includes
    an execution field with this configuration.

    This model is fully immutable:
    - Uses frozen=True to prevent attribute reassignment
    - Uses tuples instead of lists to prevent content mutation
    - Caches computed properties for performance

    Attributes:
        phases: Tuple of execution phases in order. Each phase represents a
            distinct stage in the handler execution lifecycle (e.g., preflight,
            before, execute, after, emit, finalize).
        ordering_policy: Policy for ordering handlers within phases. Controls
            how handlers are sorted and executed within each phase.
        nondeterministic_allowed_phases: Tuple of phase names where nondeterministic
            effects (e.g., random values, current time) are permitted. Must be a
            subset of the phases field.

    Properties:
        phase_order: Cached dictionary mapping phase names to their position
            indices for efficient phase ordering lookups.

    Example:
        >>> profile = ModelExecutionProfile(
        ...     phases=("init", "execute", "cleanup"),
        ...     nondeterministic_allowed_phases=("execute",),
        ... )
        >>> profile.phase_order
        {'init': 0, 'execute': 1, 'cleanup': 2}
        >>> "execute" in profile.nondeterministic_allowed_phases
        True

    See Also:
        - OMN-1227: ProtocolConstraintValidator for SPI
        - OMN-1292: Core Models for ProtocolConstraintValidator

    .. versionchanged:: 0.6.0
        Added nondeterministic_allowed_phases and phase_order property (OMN-1292)

    .. versionchanged:: 0.6.1
        Converted list fields to tuples for true immutability.
        Added cached phase_order property for performance.
        Enhanced validation for nondeterministic_allowed_phases (OMN-1292)
    """

    phases: tuple[str, ...] = Field(
        default=DEFAULT_EXECUTION_PHASES,
        description="Execution phases in order (immutable tuple)",
    )

    ordering_policy: ModelExecutionOrderingPolicy = Field(
        default_factory=ModelExecutionOrderingPolicy,
        description="Policy for ordering handlers within phases",
    )

    nondeterministic_allowed_phases: tuple[str, ...] = Field(
        default=(),
        description="Phases where nondeterministic effects are permitted (immutable tuple)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
        from_attributes=True,
    )

    @field_validator("phases", mode="before")
    @classmethod
    def coerce_phases_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """
        Coerce phases input to tuple and normalize entries.

        Normalizes input by converting to tuple and stripping whitespace
        from each entry. This enables standard Pydantic validation patterns.

        Args:
            v: Input phases as list or tuple of strings.

        Returns:
            Normalized tuple of phase names.

        Raises:
            ValueError: If any phase is empty after stripping.
        """
        if isinstance(v, list):
            v = tuple(v)
        # Normalize: strip whitespace
        normalized = tuple(phase.strip() for phase in v)
        return normalized

    @field_validator("nondeterministic_allowed_phases", mode="before")
    @classmethod
    def coerce_nondeterministic_phases_to_tuple(
        cls, v: list[str] | tuple[str, ...]
    ) -> tuple[str, ...]:
        """
        Coerce nondeterministic_allowed_phases input to tuple with validation.

        Normalizes input by converting to tuple, stripping whitespace,
        and removing duplicates while preserving order.

        Args:
            v: Input phases as list or tuple of strings.

        Returns:
            Normalized, deduplicated tuple of phase names.

        Raises:
            ValueError: If any phase is empty after stripping.
        """
        if isinstance(v, list):
            v = tuple(v)
        # Normalize: strip whitespace
        normalized = tuple(phase.strip() for phase in v)
        # Remove duplicates while preserving order
        seen: set[str] = set()
        deduplicated: list[str] = []
        for phase in normalized:
            if phase not in seen:
                seen.add(phase)
                deduplicated.append(phase)
        return tuple(deduplicated)

    @cached_property
    def phase_order(self) -> dict[str, int]:
        """
        Phase -> position mapping derived from phases tuple.

        This property is cached for performance - the dictionary is computed
        once on first access and then reused for subsequent accesses.

        Returns:
            Dictionary mapping phase names to their zero-based position indices.
            The mapping is immutable in practice since the underlying phases
            tuple is immutable.

        Example:
            >>> profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))
            >>> profile.phase_order
            {'init': 0, 'execute': 1, 'cleanup': 2}
            >>> profile.phase_order["execute"]
            1

        Note:
            Since the model is frozen and phases is a tuple, the phase_order
            dictionary will always be consistent with the phases tuple.
        """
        return {phase: idx for idx, phase in enumerate(self.phases)}

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        """
        Validate profile invariants after all field validators have run.

        Ensures:
        - phases are unique (no duplicate phase names)
        - phases are non-empty strings (not empty or whitespace-only)
        - nondeterministic_allowed_phases is a subset of phases
        - nondeterministic_allowed_phases entries are non-empty strings

        Returns:
            The validated profile instance.

        Raises:
            ValueError: If any validation constraint is violated.
                - "phases must contain unique values" if duplicates found
                - "phases must be non-empty strings" if empty/whitespace phase found
                - "nondeterministic_allowed_phases must be non-empty strings" if invalid
                - "nondeterministic_allowed_phases contains phases not in phases: [...]"
                  if invalid phase references found
        """
        # Validate phases are unique
        if len(self.phases) != len(set(self.phases)):
            raise ValueError("phases must contain unique values")

        # Validate phases are non-empty strings
        for phase in self.phases:
            if not phase or not phase.strip():
                raise ValueError("phases must be non-empty strings")

        # Validate nondeterministic_allowed_phases entries are non-empty strings
        for phase in self.nondeterministic_allowed_phases:
            if not phase or not phase.strip():
                raise ValueError(
                    "nondeterministic_allowed_phases must be non-empty strings"
                )

        # Validate nondeterministic_allowed_phases is subset of phases
        phases_set = set(self.phases)
        invalid_phases = set(self.nondeterministic_allowed_phases) - phases_set
        if invalid_phases:
            raise ValueError(
                f"nondeterministic_allowed_phases contains phases not in phases: "
                f"{sorted(invalid_phases)}"
            )

        return self
