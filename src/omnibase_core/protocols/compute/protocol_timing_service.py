"""
ProtocolTimingService - Protocol for computation timing and metrics.

This protocol defines the interface for timing computation operations in NodeCompute.
By using a protocol instead of direct time module usage, NodeCompute can remain pure
while timing/metrics logic is handled by infrastructure layer implementations.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations provide the actual timing mechanism. This allows
    NodeCompute to report timing metrics without importing time module.

Architecture:
    NodeCompute receives an optional timing service via container. If provided,
    the service is used for measuring computation duration. If not provided,
    NodeCompute operates without timing (pure mode, returns 0.0 for processing_time_ms).

Usage:
    .. code-block:: python

        from omnibase_core.protocols.compute import ProtocolTimingService

        class PerfCounterTimingService(ProtocolTimingService):
            def start_timer(self) -> float:
                return time.perf_counter()

            def stop_timer(self, start_time: float) -> float:
                return (time.perf_counter() - start_time) * 1000  # ms

        # Use in NodeCompute
        node = NodeCompute(container)
        # If container provides ProtocolTimingService, timing is enabled

Related:
    - OMN-700: Fix NodeCompute Purity Violations
    - NodeCompute: Consumer of this protocol

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ProtocolTimingService"]

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTimingService(Protocol):
    """
    Protocol for computation timing and metrics.

    Defines the interface for measuring computation duration with
    high-precision timing. Implementations can use various timing
    mechanisms (time.perf_counter, time.monotonic, etc.).

    Thread Safety:
        Implementations should be thread-safe as multiple computations
        may be timed concurrently.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolTimingService
            import time

            class MonotonicTimingService:
                '''Timing service using monotonic clock.'''

                def start_timer(self) -> float:
                    return time.monotonic()

                def stop_timer(self, start_time: float) -> float:
                    return (time.monotonic() - start_time) * 1000

            # Verify protocol compliance
            timing: ProtocolTimingService = MonotonicTimingService()
            assert isinstance(timing, ProtocolTimingService)

    .. versionadded:: 0.4.0
    """

    def start_timer(self) -> float:
        """
        Start a timer and return the start time.

        Returns:
            Start time as a float. The unit is implementation-specific
            but should be consistent with stop_timer().

        Example:
            .. code-block:: python

                start = timing.start_timer()
                # ... perform computation ...
                duration_ms = timing.stop_timer(start)
        """
        ...

    def stop_timer(self, start_time: float) -> float:
        """
        Stop timer and return elapsed time in milliseconds.

        Args:
            start_time: The start time from start_timer().

        Returns:
            Elapsed time in milliseconds (float).

        Example:
            .. code-block:: python

                start = timing.start_timer()
                result = expensive_computation()
                duration_ms = timing.stop_timer(start)
                print(f"Computation took {duration_ms:.2f}ms")
        """
        ...
