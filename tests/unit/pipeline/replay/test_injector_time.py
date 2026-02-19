# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ServiceTimeInjector - Time Injector for Replay Infrastructure.

Tests cover:
- Production mode (no fixed time): returns current UTC time
- Replay mode (fixed time): returns the fixed time for determinism
- Timezone correctness: always UTC
- Multiple calls determinism: same fixed time on repeated calls
- Protocol compliance: implements ProtocolTimeService
- Immutable state: fixed_time cannot change after creation

This test file follows TDD - tests are written BEFORE implementation.

.. versionadded:: 0.4.0
    Added as part of Replay Infrastructure (OMN-1116)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector


@pytest.fixture
def production_injector() -> ServiceTimeInjector:
    """Create an injector in production mode (no fixed time)."""
    from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector

    return ServiceTimeInjector()


@pytest.fixture
def fixed_time() -> datetime:
    """Create a fixed datetime for replay testing."""
    return datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)


@pytest.fixture
def replay_injector(fixed_time: datetime) -> ServiceTimeInjector:
    """Create an injector in replay mode with fixed time."""
    from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector

    return ServiceTimeInjector(fixed_time=fixed_time)


@pytest.mark.unit
class TestServiceTimeInjectorProductionMode:
    """Test ServiceTimeInjector in production mode (no fixed time)."""

    def test_now_returns_current_time_when_no_fixed_time(
        self, production_injector: ServiceTimeInjector
    ) -> None:
        """Test that now() returns current UTC time in production mode."""
        before = datetime.now(UTC)
        result = production_injector.now()
        after = datetime.now(UTC)

        # Result should be between before and after
        assert before <= result <= after
        # Result should be in UTC
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_utc_now_returns_current_utc_time(
        self, production_injector: ServiceTimeInjector
    ) -> None:
        """Test that utc_now() returns current UTC time in production mode."""
        before = datetime.now(UTC)
        result = production_injector.utc_now()
        after = datetime.now(UTC)

        # Result should be between before and after
        assert before <= result <= after
        # Result should be in UTC
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_now_and_utc_now_are_equivalent_in_production_mode(
        self, production_injector: ServiceTimeInjector
    ) -> None:
        """Test that now() and utc_now() return equivalent times."""
        # Both should return current UTC time
        now_result = production_injector.now()
        utc_now_result = production_injector.utc_now()

        # They should be very close (within 1 second)
        diff = abs((now_result - utc_now_result).total_seconds())
        assert diff < 1.0


@pytest.mark.unit
class TestServiceTimeInjectorReplayMode:
    """Test ServiceTimeInjector in replay mode (with fixed time)."""

    def test_now_returns_fixed_time_when_set(
        self, replay_injector: ServiceTimeInjector, fixed_time: datetime
    ) -> None:
        """Test that now() returns the fixed time in replay mode."""
        result = replay_injector.now()
        assert result == fixed_time

    def test_utc_now_returns_fixed_time_when_set(
        self, replay_injector: ServiceTimeInjector, fixed_time: datetime
    ) -> None:
        """Test that utc_now() returns the fixed time in replay mode."""
        result = replay_injector.utc_now()
        assert result == fixed_time

    def test_multiple_calls_return_same_fixed_time(
        self, replay_injector: ServiceTimeInjector, fixed_time: datetime
    ) -> None:
        """Test that multiple calls return the same fixed time (determinism)."""
        results = [replay_injector.now() for _ in range(10)]

        # All results should be identical
        assert all(r == fixed_time for r in results)

    def test_fixed_time_preserves_timezone(self, fixed_time: datetime) -> None:
        """Test that the fixed time preserves the UTC timezone."""
        from omnibase_core.services.replay.service_time_injector import (
            ServiceTimeInjector,
        )

        injector = ServiceTimeInjector(fixed_time=fixed_time)
        result = injector.now()

        assert result.tzinfo is not None
        assert result.tzinfo == UTC


@pytest.mark.unit
class TestServiceTimeInjectorTimezone:
    """Test timezone handling in ServiceTimeInjector."""

    def test_utc_now_returns_utc_timezone_production(
        self, production_injector: ServiceTimeInjector
    ) -> None:
        """Test that utc_now() returns time with UTC timezone in production."""
        result = production_injector.utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_utc_now_returns_utc_timezone_replay(
        self, replay_injector: ServiceTimeInjector
    ) -> None:
        """Test that utc_now() returns time with UTC timezone in replay."""
        result = replay_injector.utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_fixed_time_without_timezone_gets_utc(self) -> None:
        """Test that naive datetime fixed_time raises or gets UTC."""
        from omnibase_core.services.replay.service_time_injector import (
            ServiceTimeInjector,
        )

        # Create naive datetime (no timezone)
        naive_time = datetime(2024, 6, 15, 12, 30, 45)

        # The injector should handle this gracefully - either raise or assume UTC
        # For safety, we expect it to assume UTC
        injector = ServiceTimeInjector(fixed_time=naive_time)
        result = injector.now()

        # Result should have timezone info
        assert result.tzinfo is not None
        assert result.tzinfo == UTC


@pytest.mark.unit
class TestServiceTimeInjectorProtocolCompliance:
    """Test that ServiceTimeInjector implements ProtocolTimeService correctly."""

    def test_implements_protocol(self) -> None:
        """Test that ServiceTimeInjector implements ProtocolTimeService."""
        from omnibase_core.protocols.replay.protocol_time_service import (
            ProtocolTimeService,
        )
        from omnibase_core.services.replay.service_time_injector import (
            ServiceTimeInjector,
        )

        injector = ServiceTimeInjector()

        # Protocol compliance check
        assert isinstance(injector, ProtocolTimeService)

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that ProtocolTimeService is runtime_checkable."""
        # Should not raise - protocol is runtime_checkable

        from omnibase_core.protocols.replay.protocol_time_service import (
            ProtocolTimeService,
        )

        # The decorator should already be applied
        assert hasattr(ProtocolTimeService, "__protocol_attrs__") or hasattr(
            ProtocolTimeService, "_is_runtime_protocol"
        )

    def test_has_required_methods(
        self, production_injector: ServiceTimeInjector
    ) -> None:
        """Test that ServiceTimeInjector has all required protocol methods."""
        assert hasattr(production_injector, "now")
        assert callable(production_injector.now)
        assert hasattr(production_injector, "utc_now")
        assert callable(production_injector.utc_now)


@pytest.mark.unit
class TestServiceTimeInjectorImmutability:
    """Test ServiceTimeInjector immutability characteristics."""

    def test_fixed_time_is_stored(self, replay_injector: ServiceTimeInjector) -> None:
        """Test that fixed_time is properly stored."""
        # The internal state should be immutable once set
        # We can verify by checking multiple accesses return same value
        results = [replay_injector.now() for _ in range(5)]
        assert len(set(results)) == 1  # All identical

    def test_none_fixed_time_allows_production_mode(
        self, production_injector: ServiceTimeInjector
    ) -> None:
        """Test that None fixed_time enables production mode."""
        # Should return current time, not raise
        result = production_injector.now()
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC


@pytest.mark.unit
class TestServiceTimeInjectorEdgeCases:
    """Test edge cases for ServiceTimeInjector."""

    def test_epoch_fixed_time(self) -> None:
        """Test with Unix epoch as fixed time."""
        from omnibase_core.services.replay.service_time_injector import (
            ServiceTimeInjector,
        )

        epoch = datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
        injector = ServiceTimeInjector(fixed_time=epoch)

        result = injector.now()
        assert result == epoch

    def test_far_future_fixed_time(self) -> None:
        """Test with far future date as fixed time."""
        from omnibase_core.services.replay.service_time_injector import (
            ServiceTimeInjector,
        )

        future = datetime(2100, 12, 31, 23, 59, 59, tzinfo=UTC)
        injector = ServiceTimeInjector(fixed_time=future)

        result = injector.now()
        assert result == future

    def test_microsecond_precision(self) -> None:
        """Test that microsecond precision is preserved."""
        from omnibase_core.services.replay.service_time_injector import (
            ServiceTimeInjector,
        )

        precise_time = datetime(2024, 6, 15, 12, 30, 45, microsecond=123456, tzinfo=UTC)
        injector = ServiceTimeInjector(fixed_time=precise_time)

        result = injector.now()
        assert result.microsecond == 123456
