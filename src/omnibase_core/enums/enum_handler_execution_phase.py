"""
Handler Execution Phase Enum.

Defines the canonical execution phases for handler processing in the ONEX
Runtime Execution Sequencing Model. These phases align with the pipeline
convention defined in DEFAULT_EXECUTION_PHASES.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerExecutionPhase(StrValueHelper, str, Enum):
    """
    Canonical execution phases for handler processing.

    This enum defines the ordered phases of handler execution in the ONEX
    runtime. Each phase has a specific purpose in the execution lifecycle:

    1. PREFLIGHT: Validation and setup before main execution
    2. BEFORE: Pre-processing hooks and preparation
    3. EXECUTE: Core handler logic execution
    4. AFTER: Post-processing hooks and cleanup
    5. EMIT: Event emission and notification
    6. FINALIZE: Final cleanup and resource release

    The phases are ordered and must execute in sequence: PREFLIGHT -> BEFORE ->
    EXECUTE -> AFTER -> EMIT -> FINALIZE.

    This enum aligns with DEFAULT_EXECUTION_PHASES defined in:
    ``omnibase_core.models.contracts.model_execution_profile``

    Example:
        >>> phase = EnumHandlerExecutionPhase.EXECUTE
        >>> phase.value
        'execute'

        >>> # Use is_before() / is_after() for execution order comparison
        >>> EnumHandlerExecutionPhase.PREFLIGHT.is_before(EnumHandlerExecutionPhase.EXECUTE)
        True

        >>> # Create from string value
        >>> EnumHandlerExecutionPhase("before")
        <EnumHandlerExecutionPhase.BEFORE: 'before'>

    Note:
        The ``<`` and ``>`` operators compare string values lexicographically,
        NOT by execution order. Use :meth:`is_before` and :meth:`is_after` for
        execution order comparisons.

    See Also:
        - :const:`~omnibase_core.models.contracts.model_execution_profile.DEFAULT_EXECUTION_PHASES`:
          The list of default phases that this enum represents
        - :class:`~omnibase_core.models.contracts.model_execution_profile.ModelExecutionProfile`:
          Profile model that uses these phases

    .. versionadded:: 0.4.0
        Added as part of Runtime Execution Sequencing Model (OMN-1108)
    """

    PREFLIGHT = "preflight"
    """Validation and setup phase before main execution begins."""

    BEFORE = "before"
    """Pre-processing hooks and preparation phase."""

    EXECUTE = "execute"
    """Core handler logic execution phase."""

    AFTER = "after"
    """Post-processing hooks and cleanup phase."""

    EMIT = "emit"
    """Event emission and notification phase."""

    FINALIZE = "finalize"
    """Final cleanup and resource release phase."""

    @classmethod
    def get_ordered_phases(cls) -> list[EnumHandlerExecutionPhase]:
        """
        Return all phases in their canonical execution order.

        Returns:
            List of phases in order: PREFLIGHT, BEFORE, EXECUTE, AFTER, EMIT, FINALIZE
        """
        return [
            cls.PREFLIGHT,
            cls.BEFORE,
            cls.EXECUTE,
            cls.AFTER,
            cls.EMIT,
            cls.FINALIZE,
        ]

    @classmethod
    def get_phase_index(cls, phase: EnumHandlerExecutionPhase) -> int:
        """
        Get the index of a phase in the execution order.

        Args:
            phase: The phase to get the index for

        Returns:
            Zero-based index of the phase in execution order
        """
        return cls.get_ordered_phases().index(phase)

    def is_before(self, other: EnumHandlerExecutionPhase) -> bool:
        """
        Check if this phase executes before another phase.

        Args:
            other: The phase to compare against

        Returns:
            True if this phase executes before the other phase
        """
        return self.get_phase_index(self) < self.get_phase_index(other)

    def is_after(self, other: EnumHandlerExecutionPhase) -> bool:
        """
        Check if this phase executes after another phase.

        Args:
            other: The phase to compare against

        Returns:
            True if this phase executes after the other phase
        """
        return self.get_phase_index(self) > self.get_phase_index(other)


# Export for use
__all__ = ["EnumHandlerExecutionPhase"]
