"""
ProtocolTimeService - Protocol for time injection in replay infrastructure.

This protocol defines the interface for time injection in the ONEX pipeline,
enabling deterministic replay by fixing time during execution.

Design:
    Uses dependency inversion - Core defines the interface, and implementations
    provide either production time (current UTC) or fixed time for replay.

Architecture:
    Pipeline context receives a time service via injection. If a fixed time is
    provided, the service returns that time for deterministic replay. If not,
    the service returns current UTC time (production mode).

Usage:
    .. code-block:: python

        from omnibase_core.protocols.replay import ProtocolTimeService
        from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector
        from datetime import datetime, timezone

        # Production mode - returns current time
        time_service: ProtocolTimeService = ServiceTimeInjector()
        current = time_service.now()

        # Replay mode - returns fixed time
        fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        replay_service: ProtocolTimeService = ServiceTimeInjector(fixed_time=fixed)
        replayed = replay_service.now()  # Always returns fixed time

Related:
    - OMN-1116: Implement Time Injector for Replay Infrastructure
    - ServiceTimeInjector: Default implementation
    - ctx.time.now(): Pattern for accessing time in pipeline context

.. versionadded:: 0.4.0
"""

__all__ = ["ProtocolTimeService"]

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTimeService(Protocol):
    """
    Protocol for time injection in replay infrastructure.

    Defines the interface for obtaining the current time in a way that
    can be controlled for deterministic replay. Implementations may
    return current time (production mode) or a fixed time (replay mode).

    Thread Safety:
        Implementations should be thread-safe as multiple pipeline stages
        may access time concurrently.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.replay import ProtocolTimeService
            from datetime import datetime, timezone

            class MockTimeService:
                '''Test implementation returning fixed time.'''

                def __init__(self) -> None:
                    self._fixed = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

                def now(self) -> datetime:
                    return self._fixed

                def utc_now(self) -> datetime:
                    return self._fixed

            # Verify protocol compliance
            time_svc: ProtocolTimeService = MockTimeService()
            assert isinstance(time_svc, ProtocolTimeService)

    .. versionadded:: 0.4.0
    """

    def now(self) -> datetime:
        """
        Return the current time.

        In production mode, returns the actual current UTC time.
        In replay mode, returns the fixed time set during initialization.

        Returns:
            datetime: Current time with timezone info (always UTC).

        Example:
            .. code-block:: python

                time_service = ServiceTimeInjector()
                current = time_service.now()
                print(f"Current time: {current.isoformat()}")
        """
        ...

    def utc_now(self) -> datetime:
        """
        Return the current UTC time.

        This method is an alias for now() to explicitly indicate UTC.
        Both methods return identical results in this implementation.

        Returns:
            datetime: Current UTC time with timezone.utc tzinfo.

        Example:
            .. code-block:: python

                time_service = ServiceTimeInjector()
                utc_time = time_service.utc_now()
                assert utc_time.tzinfo == timezone.utc
        """
        ...
