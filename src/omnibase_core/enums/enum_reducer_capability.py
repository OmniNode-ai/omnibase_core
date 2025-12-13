"""
Reducer Capability Enumeration.

Defines the available capabilities for REDUCER nodes in the ONEX four-node architecture.
REDUCER nodes handle state aggregation and management including state machines (FSM),
accumulators, and event reduction.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumReducerCapability(str, Enum):
    """
    Enumeration of supported reducer node capabilities.

    SINGLE SOURCE OF TRUTH for reducer capability values.
    Replaces magic strings in handler capability constants.

    Using an enum instead of raw strings:
    - Prevents typos ("fsm_interpreter" vs "fsmInterpreter")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes capability definitions
    - Preserves full type safety

    Capabilities:
        FSM_INTERPRETER: Finite State Machine interpreter capability

    Example:
        >>> from omnibase_core.enums import EnumReducerCapability
        >>> cap = EnumReducerCapability.FSM_INTERPRETER
        >>> str(cap)
        'fsm_interpreter'
        >>> cap.value
        'fsm_interpreter'
    """

    FSM_INTERPRETER = "fsm_interpreter"
    """Finite State Machine interpreter capability for state management."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all capability values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match capability:
                case EnumReducerCapability.FSM_INTERPRETER:
                    handle_fsm()
                case _ as unreachable:
                    EnumReducerCapability.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumReducerCapability"]
