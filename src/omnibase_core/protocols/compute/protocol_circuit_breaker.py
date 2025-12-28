"""
ProtocolCircuitBreaker - Protocol for circuit breaker implementations.

This protocol defines the interface for circuit breaker pattern implementations,
enabling duck typing across different implementations in omnibase_core (sync)
and omnibase_infra (async) without requiring direct inheritance.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations (ModelCircuitBreaker, MixinAsyncCircuitBreaker, or custom)
    satisfy the contract. This enables consistent circuit breaker behavior
    across the ONEX ecosystem while allowing implementation flexibility.

Thread Safety:
    WARNING: Thread safety is implementation-specific. Callers should verify
    the thread safety guarantees of their chosen implementation.

    - ModelCircuitBreaker (omnibase_core): NOT thread-safe
    - MixinAsyncCircuitBreaker (omnibase_infra): Thread-safe via asyncio

Usage:
    .. code-block:: python

        from typing import Callable, TypeVar
        from omnibase_core.protocols.compute import ProtocolCircuitBreaker

        T = TypeVar("T")

        def execute_with_circuit_breaker(
            circuit_breaker: ProtocolCircuitBreaker,
            operation: Callable[[], T],
        ) -> T:
            '''Execute operation with circuit breaker protection.'''
            if circuit_breaker.is_open:
                raise CircuitOpenError("Circuit breaker is open")

            try:
                result = operation()
                circuit_breaker.record_success()
                return result
            except Exception:  # Example: Recording failures before re-raising
                circuit_breaker.record_failure()
                raise

Related:
    - OMN-861: Define ProtocolCircuitBreaker interface
    - ModelCircuitBreaker: Sync implementation in omnibase_core
    - MixinAsyncCircuitBreaker: Async implementation in omnibase_infra
    - docs/analysis/CIRCUIT_BREAKER_COMPARISON.md: Implementation comparison

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = [
    "ProtocolCircuitBreaker",
    "ProtocolAsyncCircuitBreaker",
]

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolCircuitBreaker(Protocol):
    """
    Protocol for synchronous circuit breaker implementations.

    Defines the minimal interface for circuit breaker pattern implementations
    that operate synchronously. This protocol is designed to be compatible
    with existing ModelCircuitBreaker while providing a standard interface
    for dependency injection and duck typing.

    States:
        - **closed**: Normal operation, requests pass through
        - **open**: Circuit tripped, requests are rejected
        - **half_open**: Testing recovery, limited requests allowed

    Thread Safety:
        WARNING: Implementations are NOT guaranteed to be thread-safe.
        See implementation-specific documentation for thread safety guarantees.

        Mitigation Options:
        1. **Thread-local instances**: Each thread gets its own circuit breaker
        2. **Synchronized wrapper**: Wrap with threading.Lock
        3. **Single-threaded access**: Ensure only one thread accesses the instance

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolCircuitBreaker

            class SimpleCircuitBreaker:
                '''Minimal circuit breaker implementation.'''

                def __init__(self, failure_threshold: int = 5):
                    self._failure_count = 0
                    self._failure_threshold = failure_threshold
                    self._is_open = False

                @property
                def is_open(self) -> bool:
                    return self._is_open

                @property
                def failure_count(self) -> int:
                    return self._failure_count

                def record_success(self) -> None:
                    self._failure_count = 0
                    self._is_open = False

                def record_failure(self, correlation_id: UUID | None = None) -> None:
                    self._failure_count += 1
                    if self._failure_count >= self._failure_threshold:
                        self._is_open = True

                def reset(self) -> None:
                    self._failure_count = 0
                    self._is_open = False

            # Verify protocol conformance
            cb: ProtocolCircuitBreaker = SimpleCircuitBreaker()
            assert isinstance(cb, ProtocolCircuitBreaker)

    .. versionadded:: 0.4.0
    """

    @property
    def is_open(self) -> bool:
        """
        Check if circuit breaker is currently open (rejecting requests).

        Returns:
            True if circuit is open and requests should be rejected,
            False if circuit is closed or half-open and requests may proceed.

        Note:
            For implementations with half-open state, this should return
            False during half-open to allow probe requests.
        """
        ...

    @property
    def failure_count(self) -> int:
        """
        Get current failure count within the tracking window.

        Returns:
            Number of failures recorded in the current tracking window.
            The exact semantics depend on the implementation's windowing
            strategy (sliding window, tumbling window, etc.).

        Note:
            This count may be reset when transitioning between states
            or when the time window expires.
        """
        ...

    def record_success(self) -> None:
        """
        Record a successful operation.

        This method should be called after each successful operation to:
        - Track success metrics
        - Progress state transitions (e.g., half-open -> closed)
        - Reset failure counters if applicable

        Note:
            In half-open state, sufficient successes may transition
            the circuit breaker back to closed state.
        """
        ...

    def record_failure(self, correlation_id: UUID | None = None) -> None:
        """
        Record a failed operation.

        This method should be called after each failed operation to:
        - Increment failure counters
        - Evaluate whether to open the circuit
        - Track failure metrics with optional correlation

        Args:
            correlation_id: Optional UUID for correlating failures across
                distributed systems. Implementations may use this for
                logging, tracing, or distributed circuit breaker coordination.
                Pass None if correlation tracking is not needed.

        Note:
            The ``correlation_id`` parameter is optional and implementations may vary
            in how they utilize it:

            - Simple implementations may ignore it entirely
            - Observability-focused implementations may log it for distributed tracing
            - Analytics implementations may aggregate metrics by correlation_id

            Protocol conformance requires accepting the parameter but does not
            mandate any specific behavior.
        """
        ...

    def reset(self) -> None:
        """
        Manually reset circuit breaker to closed state.

        Resets all counters and state to initial values:
        - State transitions to closed
        - Failure and success counters reset to zero
        - Any timing-related state is cleared

        Use Cases:
            - Manual recovery after fixing underlying issues
            - Testing and development scenarios
            - Forced recovery when automatic recovery isn't working

        Warning:
            Calling reset() while underlying issues persist may lead to
            immediate re-opening of the circuit. Use with caution.
        """
        ...


@runtime_checkable
class ProtocolAsyncCircuitBreaker(Protocol):
    """
    Protocol for asynchronous circuit breaker implementations.

    Defines the interface for circuit breaker implementations that operate
    asynchronously, typically used in async/await contexts with asyncio.
    This protocol mirrors ProtocolCircuitBreaker but uses async methods.

    States:
        - **closed**: Normal operation, requests pass through
        - **open**: Circuit tripped, requests are rejected
        - **half_open**: Testing recovery, limited requests allowed

    Thread Safety:
        Async implementations typically use asyncio primitives (locks, events)
        for coordination, making them safe for concurrent coroutine access
        but NOT for multi-threaded access.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolAsyncCircuitBreaker

            class AsyncCircuitBreaker:
                '''Async circuit breaker with lock protection.'''

                def __init__(self, failure_threshold: int = 5):
                    self._failure_count = 0
                    self._failure_threshold = failure_threshold
                    self._is_open = False
                    self._lock = asyncio.Lock()

                @property
                def is_open(self) -> bool:
                    return self._is_open

                @property
                def failure_count(self) -> int:
                    return self._failure_count

                async def record_success(self) -> None:
                    async with self._lock:
                        self._failure_count = 0
                        self._is_open = False

                async def record_failure(self, correlation_id: UUID | None = None) -> None:
                    async with self._lock:
                        self._failure_count += 1
                        if self._failure_count >= self._failure_threshold:
                            self._is_open = True

                async def reset(self) -> None:
                    async with self._lock:
                        self._failure_count = 0
                        self._is_open = False

            # Usage in async context
            async def protected_call(cb: ProtocolAsyncCircuitBreaker):
                if cb.is_open:
                    raise CircuitOpenError("Circuit is open")
                try:
                    result = await external_service_call()
                    await cb.record_success()
                    return result
                except Exception:  # Example: Recording failures before re-raising
                    await cb.record_failure()
                    raise

    .. versionadded:: 0.4.0
    """

    @property
    def is_open(self) -> bool:
        """
        Check if circuit breaker is currently open (rejecting requests).

        Returns:
            True if circuit is open and requests should be rejected,
            False if circuit is closed or half-open and requests may proceed.

        Note:
            This is a synchronous property for efficient checking.
            State-changing operations are async.
        """
        ...

    @property
    def failure_count(self) -> int:
        """
        Get current failure count within the tracking window.

        Returns:
            Number of failures recorded in the current tracking window.

        Note:
            This is a synchronous property for efficient access.
        """
        ...

    async def record_success(self) -> None:
        """
        Record a successful operation asynchronously.

        This method should be called after each successful operation to:
        - Track success metrics
        - Progress state transitions (e.g., half-open -> closed)
        - Reset failure counters if applicable

        Note:
            Async to allow for distributed state synchronization or
            async logging/metrics reporting.
        """
        ...

    async def record_failure(self, correlation_id: UUID | None = None) -> None:
        """
        Record a failed operation asynchronously.

        Args:
            correlation_id: Optional UUID for correlating failures across
                distributed systems.

        Note:
            Async to allow for distributed state updates or
            async logging/metrics reporting.

            The ``correlation_id`` parameter is optional and implementations may vary
            in how they utilize it:

            - Simple implementations may ignore it entirely
            - Observability-focused implementations may log it for distributed tracing
            - Analytics implementations may aggregate metrics by correlation_id

            Protocol conformance requires accepting the parameter but does not
            mandate any specific behavior.
        """
        ...

    async def reset(self) -> None:
        """
        Manually reset circuit breaker to closed state asynchronously.

        Resets all counters and state to initial values.

        Warning:
            Calling reset() while underlying issues persist may lead to
            immediate re-opening of the circuit.
        """
        ...
