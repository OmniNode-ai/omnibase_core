"""
Reducer Capability Enumeration.

Defines the available capabilities for REDUCER nodes in the ONEX four-node architecture.
REDUCER nodes handle state aggregation and management including state machines (FSM),
accumulators, and event reduction.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumReducerCapability(StrValueHelper, str, Enum):
    """Reducer node capabilities (currently: FSM_INTERPRETER for state management)."""

    FSM_INTERPRETER = "fsm_interpreter"
    """Finite State Machine interpreter capability for state management."""

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
