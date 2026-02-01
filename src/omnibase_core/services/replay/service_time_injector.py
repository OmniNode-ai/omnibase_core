"""
ServiceTimeInjector - Time injector for deterministic replay.

This module provides the default ProtocolTimeService implementation for
controlled time injection in the ONEX pipeline.

Design:
    When fixed_time is provided (replay mode), all time queries return
    that fixed time for deterministic execution. When fixed_time is None
    (production mode), queries return the current UTC time.

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector
        from datetime import datetime, timezone

        # Production mode: returns current time
        time_svc = ServiceTimeInjector()
        current = time_svc.now()

        # Replay mode: returns fixed time
        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_svc = ServiceTimeInjector(fixed_time=fixed)
        replayed = time_svc.now()  # Always returns fixed time

Key Invariant:
    Fixed time -> Same result (determinism for replay)

    .. code-block:: python

        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        time1 = ServiceTimeInjector(fixed_time=fixed)
        time2 = ServiceTimeInjector(fixed_time=fixed)
        assert time1.now() == time2.now() == fixed

Thread Safety:
    ServiceTimeInjector is thread-safe. The fixed_time is immutable after
    initialization, and datetime.now() is thread-safe.

Related:
    - OMN-1116: Time Injector for Replay Infrastructure
    - MIXINS_TO_HANDLERS_REFACTOR.md Section 7.1
    - ProtocolTimeService: Protocol definition
    - ctx.time.now(): Pattern for accessing time in pipeline context

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceTimeInjector"]

from datetime import UTC, datetime

from omnibase_core.protocols.replay import ProtocolTimeService


class ServiceTimeInjector:
    """
    Time injector for deterministic replay.

    When fixed_time is set, always returns that time (replay mode).
    When None, returns current UTC time (production mode).

    Args:
        fixed_time: Optional fixed datetime for replay mode. If provided,
            all time queries return this value. If None, returns current
            UTC time.

    Attributes:
        fixed_time: The fixed time used for replay, or None for production.

    Example:
        >>> from datetime import datetime, timezone
        >>> # Production mode
        >>> time_svc = ServiceTimeInjector()
        >>> current = time_svc.now()  # Returns current UTC time
        >>> assert current.tzinfo == timezone.utc
        >>>
        >>> # Replay mode
        >>> fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        >>> time_svc = ServiceTimeInjector(fixed_time=fixed)
        >>> time_svc.now()
        datetime.datetime(2024, 6, 15, 12, 0, tzinfo=datetime.timezone.utc)

    Thread Safety:
        Thread-safe. The fixed_time is immutable after initialization.

    .. versionadded:: 0.4.0
    """

    def __init__(self, fixed_time: datetime | None = None) -> None:
        """
        Initialize the time injector.

        Args:
            fixed_time: Optional fixed datetime for replay mode.
                If None, production mode is enabled (returns current time).
                If provided without timezone info (naive datetime),
                UTC is assumed.
        """
        if fixed_time is not None:
            # Ensure timezone is set - assume UTC for naive datetimes
            if fixed_time.tzinfo is None:
                fixed_time = fixed_time.replace(tzinfo=UTC)
            self._fixed: datetime | None = fixed_time
        else:
            self._fixed = None

    @property
    def fixed_time(self) -> datetime | None:
        """
        Return the fixed time used for replay, or None for production mode.

        Returns:
            The fixed datetime if in replay mode, None if in production mode.

        Example:
            >>> fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
            >>> time_svc = ServiceTimeInjector(fixed_time=fixed)
            >>> time_svc.fixed_time == fixed
            True
            >>> prod_svc = ServiceTimeInjector()
            >>> prod_svc.fixed_time is None
            True
        """
        return self._fixed

    def now(self) -> datetime:
        """
        Return the current time.

        In production mode, returns the actual current UTC time.
        In replay mode, returns the fixed time set during initialization.

        Returns:
            datetime: Current time with timezone info (always UTC).

        Example:
            >>> time_svc = ServiceTimeInjector()
            >>> current = time_svc.now()
            >>> assert current.tzinfo == timezone.utc
            >>>
            >>> fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            >>> replay_svc = ServiceTimeInjector(fixed_time=fixed)
            >>> replay_svc.now() == fixed
            True
        """
        if self._fixed is not None:
            return self._fixed
        return datetime.now(UTC)

    def utc_now(self) -> datetime:
        """
        Return the current UTC time.

        This method is an alias for now() to explicitly indicate UTC.
        Both methods return identical results in this implementation.

        Returns:
            datetime: Current UTC time with timezone.utc tzinfo.

        Example:
            >>> time_svc = ServiceTimeInjector()
            >>> utc = time_svc.utc_now()
            >>> assert utc.tzinfo == timezone.utc
        """
        return self.now()


# Verify protocol compliance at module load time
_time_check: ProtocolTimeService = ServiceTimeInjector()
