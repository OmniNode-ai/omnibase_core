"""Circuit breaker state enumeration (CLOSED, OPEN, HALF_OPEN)."""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

__all__ = ["EnumCircuitBreakerState"]


@unique
class EnumCircuitBreakerState(Enum):
    """
    Circuit breaker state enumeration.

    CLOSED: Normal operation. OPEN: Requests rejected. HALF_OPEN: Testing recovery.
    """

    CLOSED = "closed"
    """Normal operation, requests pass through."""

    OPEN = "open"
    """Circuit tripped, requests are rejected."""

    HALF_OPEN = "half_open"
    """Testing recovery, limited requests allowed."""

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensure exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            .. code-block:: python

                match circuit_state:
                    case EnumCircuitBreakerState.CLOSED:
                        handle_closed()
                    case EnumCircuitBreakerState.OPEN:
                        handle_open()
                    case EnumCircuitBreakerState.HALF_OPEN:
                        handle_half_open()
                    case _ as unreachable:
                        EnumCircuitBreakerState.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.

        .. versionadded:: 0.4.0
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")
