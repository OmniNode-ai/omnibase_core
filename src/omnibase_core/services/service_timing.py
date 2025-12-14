"""
ServiceTiming - Default ProtocolTimingService implementation.

Provides high-precision timing using time.perf_counter.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import time

from omnibase_core.protocols.compute import ProtocolTimingService

__all__ = ["ServiceTiming"]


class ServiceTiming:
    """
    Default ProtocolTimingService implementation using time.perf_counter.

    Provides high-precision timing using Python's time.perf_counter,
    which is monotonic and unaffected by system clock adjustments.

    Thread Safety:
        Thread-safe. Uses thread-safe system calls.

    Example:
        >>> timing = ServiceTiming()
        >>> start = timing.start_timer()
        >>> # ... do work ...
        >>> duration_ms = timing.stop_timer(start)

    .. versionadded:: 0.4.0
    """

    def start_timer(self) -> float:
        """Start a timer using perf_counter."""
        return time.perf_counter()

    def stop_timer(self, start_time: float) -> float:
        """Stop timer and return elapsed time in milliseconds."""
        return (time.perf_counter() - start_time) * 1000


# Verify protocol compliance
_timing_check: ProtocolTimingService = ServiceTiming()
