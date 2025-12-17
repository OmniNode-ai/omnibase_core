"""
EnumCircuitBreakerState - Circuit breaker state enumeration.

Defines the standard states for circuit breaker implementations.
Used by ProtocolCircuitBreaker implementations for type-safe state checking.

Related:
    - OMN-861: Define ProtocolCircuitBreaker interface
    - ProtocolCircuitBreaker: Protocol that uses these states

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from enum import Enum
from typing import Never, NoReturn

__all__ = ["EnumCircuitBreakerState"]


class EnumCircuitBreakerState(Enum):
    """
    Circuit breaker state enumeration.

    The circuit breaker pattern prevents cascading failures by tracking the
    health of external dependencies and temporarily blocking requests when
    failures exceed a threshold.

    States:
        CLOSED: Normal operation, requests pass through. The circuit monitors
            for failures and transitions to OPEN if the failure threshold is exceeded.
        OPEN: Circuit tripped, requests are rejected immediately without attempting
            the operation. After a timeout period, transitions to HALF_OPEN.
        HALF_OPEN: Testing recovery, limited requests allowed through to probe
            whether the service has recovered. Success returns to CLOSED,
            failure returns to OPEN.

    State Transitions::

        CLOSED --[failure threshold exceeded]--> OPEN
        OPEN --[timeout elapsed]--> HALF_OPEN
        HALF_OPEN --[probe succeeds]--> CLOSED
        HALF_OPEN --[probe fails]--> OPEN

    Example:
        .. code-block:: python

            from omnibase_core.enums import EnumCircuitBreakerState

            state = EnumCircuitBreakerState.CLOSED
            if state == EnumCircuitBreakerState.OPEN:
                raise CircuitOpenError("Circuit is open")

            # Using in match statement with exhaustive checking
            match state:
                case EnumCircuitBreakerState.CLOSED:
                    result = execute_request()
                case EnumCircuitBreakerState.OPEN:
                    raise CircuitOpenError("Circuit is open")
                case EnumCircuitBreakerState.HALF_OPEN:
                    result = execute_probe_request()
                case _ as unreachable:
                    EnumCircuitBreakerState.assert_exhaustive(unreachable)

    .. versionadded:: 0.4.0
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
