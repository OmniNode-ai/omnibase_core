"""
Deterministic utilities for development and testing.

⚠️  WARNING: DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

This module provides deterministic clock and ID generation utilities
for reproducible testing and debugging of workflow orchestration systems.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

logger = logging.getLogger(__name__)


class DeterministicClock:
    """
    ⚠️  DEV/TEST ONLY - Deterministic Clock for Testing ⚠️

    Provides controllable time progression for deterministic testing
    of time-sensitive workflow orchestration logic.
    """

    def __init__(self, start_time: datetime | None = None):
        """
        Initialize deterministic clock.

        Args:
            start_time: Starting time (defaults to epoch)
        """
        logger.warning(
            "🚨 DeterministicClock: DEV/TEST ONLY - NEVER USE IN PRODUCTION 🚨"
        )

        if start_time is None:
            # Default to Unix epoch for deterministic testing
            start_time = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        self._current_time = start_time
        self._initial_time = start_time

        logger.info(f"⏰ DeterministicClock initialized at {self._current_time}")

    def now(self) -> datetime:
        """Get current time from deterministic clock."""
        return self._current_time

    def utcnow(self) -> datetime:
        """Get current UTC time from deterministic clock."""
        return self._current_time.replace(tzinfo=timezone.utc)

    def advance_seconds(self, seconds: float) -> datetime:
        """
        Advance clock by specified seconds.

        Args:
            seconds: Seconds to advance

        Returns:
            New current time
        """
        from datetime import timedelta

        self._current_time += timedelta(seconds=seconds)
        logger.debug(f"⏰ Advanced clock by {seconds}s to {self._current_time}")
        return self._current_time

    def advance_minutes(self, minutes: float) -> datetime:
        """
        Advance clock by specified minutes.

        Args:
            minutes: Minutes to advance

        Returns:
            New current time
        """
        return self.advance_seconds(minutes * 60)

    def advance_hours(self, hours: float) -> datetime:
        """
        Advance clock by specified hours.

        Args:
            hours: Hours to advance

        Returns:
            New current time
        """
        return self.advance_seconds(hours * 3600)

    def advance_days(self, days: float) -> datetime:
        """
        Advance clock by specified days.

        Args:
            days: Days to advance

        Returns:
            New current time
        """
        return self.advance_seconds(days * 86400)

    def set_time(self, new_time: datetime) -> datetime:
        """
        Set clock to specific time.

        Args:
            new_time: Time to set

        Returns:
            New current time
        """
        old_time = self._current_time
        self._current_time = new_time
        logger.debug(f"⏰ Set clock from {old_time} to {new_time}")
        return self._current_time

    def reset(self) -> datetime:
        """
        Reset clock to initial time.

        Returns:
            Initial time
        """
        old_time = self._current_time
        self._current_time = self._initial_time
        logger.debug(f"⏰ Reset clock from {old_time} to {self._initial_time}")
        return self._current_time

    def get_elapsed_seconds(self) -> float:
        """Get seconds elapsed since initial time."""
        delta = self._current_time - self._initial_time
        return delta.total_seconds()

    def get_elapsed_milliseconds(self) -> int:
        """Get milliseconds elapsed since initial time."""
        return int(self.get_elapsed_seconds() * 1000)


class FakeIdGenerator:
    """
    ⚠️  DEV/TEST ONLY - Fake ID Generator for Testing ⚠️

    Provides deterministic and sequential ID generation for reproducible
    testing of workflow orchestration systems.
    """

    def __init__(self, prefix: str = "test", start_counter: int = 1):
        """
        Initialize fake ID generator.

        Args:
            prefix: Prefix for generated IDs
            start_counter: Starting counter value
        """
        logger.warning("🚨 FakeIdGenerator: DEV/TEST ONLY - NEVER USE IN PRODUCTION 🚨")

        self._prefix = prefix
        self._counter = start_counter
        self._initial_counter = start_counter

        logger.info(
            f"🆔 FakeIdGenerator initialized with prefix '{prefix}', counter {start_counter}"
        )

    def next_id(self) -> str:
        """
        Generate next sequential ID.

        Returns:
            Sequential string ID
        """
        current_id = f"{self._prefix}_{self._counter:06d}"
        self._counter += 1
        return current_id

    def next_uuid(self) -> UUID:
        """
        Generate next deterministic UUID using UUID5 for realistic format.

        Returns:
            Deterministic UUID5 based on namespace and counter
        """
        # Use UUID5 with DNS namespace for realistic, deterministic UUIDs
        name = f"{self._prefix}-{self._counter:06d}.test.local"

        self._counter += 1
        return uuid5(NAMESPACE_DNS, name)

    def peek_next_id(self) -> str:
        """Peek at next ID without incrementing counter."""
        return f"{self._prefix}_{self._counter:06d}"

    def peek_next_uuid(self) -> UUID:
        """Peek at next UUID without incrementing counter."""
        uuid_string = f"{self._counter:032d}"
        formatted = (
            f"{uuid_string[:8]}-{uuid_string[8:12]}-{uuid_string[12:16]}-"
            f"{uuid_string[16:20]}-{uuid_string[20:32]}"
        )
        return UUID(formatted)

    def set_counter(self, counter: int) -> None:
        """Set counter to specific value."""
        old_counter = self._counter
        self._counter = counter
        logger.debug(f"🆔 Set counter from {old_counter} to {counter}")

    def reset(self) -> None:
        """Reset counter to initial value."""
        old_counter = self._counter
        self._counter = self._initial_counter
        logger.debug(f"🆔 Reset counter from {old_counter} to {self._initial_counter}")

    def get_current_counter(self) -> int:
        """Get current counter value."""
        return self._counter

    def generate_batch_ids(self, count: int) -> list[str]:
        """
        Generate batch of sequential IDs.

        Args:
            count: Number of IDs to generate

        Returns:
            List of sequential string IDs
        """
        ids = []
        for _ in range(count):
            ids.append(self.next_id())
        return ids

    def generate_batch_uuids(self, count: int) -> list[UUID]:
        """
        Generate batch of sequential UUIDs.

        Args:
            count: Number of UUIDs to generate

        Returns:
            List of sequential UUIDs
        """
        uuids = []
        for _ in range(count):
            uuids.append(self.next_uuid())
        return uuids


class DeterministicTestContext:
    """
    ⚠️  DEV/TEST ONLY - Combined Deterministic Test Context ⚠️

    Combines deterministic clock and ID generation for comprehensive
    deterministic testing environments.
    """

    def __init__(
        self,
        start_time: datetime | None = None,
        id_prefix: str = "test",
        start_counter: int = 1,
    ):
        """
        Initialize deterministic test context.

        Args:
            start_time: Starting time for clock
            id_prefix: Prefix for ID generation
            start_counter: Starting counter for IDs
        """
        logger.warning(
            "🚨 DeterministicTestContext: DEV/TEST ONLY - NEVER USE IN PRODUCTION 🚨"
        )

        self.clock = DeterministicClock(start_time)
        self.id_generator = FakeIdGenerator(id_prefix, start_counter)

        logger.info("🧪 DeterministicTestContext initialized for testing")

    def reset_all(self) -> None:
        """Reset both clock and ID generator."""
        self.clock.reset()
        self.id_generator.reset()
        logger.info("🔄 DeterministicTestContext reset to initial state")

    def advance_and_generate(
        self, seconds: float, id_count: int = 1
    ) -> tuple[datetime, list[str]]:
        """
        Advance clock and generate IDs in one operation.

        Args:
            seconds: Seconds to advance clock
            id_count: Number of IDs to generate

        Returns:
            Tuple of (new_time, generated_ids)
        """
        new_time = self.clock.advance_seconds(seconds)
        ids = self.id_generator.generate_batch_ids(id_count)
        return new_time, ids

    def get_current_state(self) -> dict[str, Any]:
        """Get current state of test context."""
        return {
            "current_time": self.clock.now().isoformat(),
            "elapsed_seconds": self.clock.get_elapsed_seconds(),
            "current_counter": self.id_generator.get_current_counter(),
            "next_id": self.id_generator.peek_next_id(),
            "next_uuid": str(self.id_generator.peek_next_uuid()),
        }


# Global instances for testing
_global_test_clock: DeterministicClock | None = None
_global_id_generator: FakeIdGenerator | None = None
_global_test_context: DeterministicTestContext | None = None


def get_test_clock() -> DeterministicClock:
    """
    Get or create global test clock.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        DeterministicClock instance
    """
    global _global_test_clock
    if _global_test_clock is None:
        _global_test_clock = DeterministicClock()
        logger.info("✅ Created global test clock")
    return _global_test_clock


def get_test_id_generator() -> FakeIdGenerator:
    """
    Get or create global test ID generator.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        FakeIdGenerator instance
    """
    global _global_id_generator
    if _global_id_generator is None:
        _global_id_generator = FakeIdGenerator()
        logger.info("✅ Created global test ID generator")
    return _global_id_generator


def get_test_context() -> DeterministicTestContext:
    """
    Get or create global test context.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        DeterministicTestContext instance
    """
    global _global_test_context
    if _global_test_context is None:
        _global_test_context = DeterministicTestContext()
        logger.info("✅ Created global test context")
    return _global_test_context


def reset_all_test_utilities() -> None:
    """
    Reset all global test utilities to initial state.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️
    """
    global _global_test_clock, _global_id_generator, _global_test_context

    if _global_test_clock:
        _global_test_clock.reset()

    if _global_id_generator:
        _global_id_generator.reset()

    if _global_test_context:
        _global_test_context.reset_all()

    logger.info("🔄 Reset all global test utilities")
