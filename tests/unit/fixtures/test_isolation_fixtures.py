"""Tests for isolation fixtures."""

import pytest

from omnibase_core.context.application_context import (
    _current_container,
    get_current_container,
    set_current_container,
)
from tests.fixtures.isolation import (
    LEGACY_HOLDER_KEYS,
    SingletonResetContext,
    clear_all_caches,
    get_all_holder_classes,
    get_current_container_for_test,
    is_legacy_holder_key,
    reset_application_context,
    reset_singleton_by_key,
)


class FakeContainer:
    """Fake container for testing."""


@pytest.mark.unit
class TestSingletonResetContext:
    """Tests for SingletonResetContext."""

    def test_reset_container_to_none(self) -> None:
        """Test that container context is reset to None inside context."""
        # Set up test value in context
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]

        try:
            with SingletonResetContext(holder_keys=["container"]):
                assert get_current_container() is None

            # Value should be restored after exiting context
            assert get_current_container() is fake_container
        finally:
            # Clean up
            _current_container.reset(token)

    def test_legacy_keys_silently_ignored(self) -> None:
        """Test that legacy keys are handled properly."""
        # Set up test value
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]

        try:
            # Include legacy keys - container should still be reset
            with SingletonResetContext(
                holder_keys=["container", "logger_cache", "protocol_cache"]
            ) as ctx:
                # Container key should be in the holder keys
                assert ctx._holder_keys == ["container"]
                assert get_current_container() is None

            # Value should be restored
            assert get_current_container() is fake_container
        finally:
            # Clean up
            _current_container.reset(token)

    def test_restore_on_exit(self) -> None:
        """Test that original values are restored on exit."""
        original_value = FakeContainer()
        token = set_current_container(original_value)  # type: ignore[arg-type]

        try:
            with SingletonResetContext(holder_keys=["container"]):
                assert get_current_container() is None

            assert get_current_container() is original_value
        finally:
            # Clean up
            _current_container.reset(token)

    def test_clear_caches_parameter(self) -> None:
        """Test that clear_caches parameter controls cache clearing."""
        # Just verify the parameter is properly handled
        with SingletonResetContext(clear_caches=True) as ctx:
            assert ctx._clear_caches is True

        with SingletonResetContext(clear_caches=False) as ctx:
            assert ctx._clear_caches is False


@pytest.mark.unit
class TestClearAllCaches:
    """Tests for clear_all_caches function."""

    def test_clear_all_caches_no_error(self) -> None:
        """Test that clear_all_caches runs without error."""
        # Should not raise any exceptions
        clear_all_caches()

    def test_clear_all_caches_idempotent(self) -> None:
        """Test that clear_all_caches can be called multiple times."""
        # Multiple calls should be safe
        clear_all_caches()
        clear_all_caches()
        clear_all_caches()


@pytest.mark.unit
class TestIsolationFixtures:
    """Tests for pytest fixtures."""

    def test_reset_container_singleton(self, reset_container_singleton: object) -> None:
        """Test that container context is reset."""
        assert get_current_container() is None

    def test_reset_all_singletons(self, reset_all_singletons: object) -> None:
        """Test that all contexts are reset and caches cleared."""
        assert get_current_container() is None
        # Note: We can't directly check lru_cache caches, but the fixture
        # clears them via clear_all_caches()

    def test_isolated_correlation_context(
        self, isolated_correlation_context: object
    ) -> None:
        """Test that correlation context is isolated."""
        from omnibase_core.logging.core_logging import get_correlation_id

        assert get_correlation_id() is None

    def test_reset_registries_fixture(self, reset_registries: None) -> None:
        """Test that reset_registries fixture clears caches and container."""
        # Container context should be reset
        assert get_current_container() is None

    def test_clear_caches_fixture(self, clear_caches_fixture: None) -> None:
        """Test that clear_caches_fixture clears caches."""
        # Just verify it runs without error


@pytest.mark.unit
class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_all_holder_classes_empty(self) -> None:
        """Test that no holder classes are returned (all migrated)."""
        holders = get_all_holder_classes()
        # Now returns empty dict - all holders have been removed
        assert len(holders) == 0

    def test_reset_singleton_by_key_container(self) -> None:
        """Test resetting the container context."""
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]

        try:
            result = reset_singleton_by_key("container")
            assert result is True
            assert get_current_container() is None
        finally:
            # Clean up
            _current_container.reset(token)

    def test_reset_singleton_by_key_legacy_returns_true(self) -> None:
        """Test that resetting legacy keys returns True and clears caches."""
        # Legacy keys should return True (they clear caches instead)
        result = reset_singleton_by_key("logger_cache")
        assert result is True

        result = reset_singleton_by_key("protocol_cache")
        assert result is True

        result = reset_singleton_by_key("action_registry")
        assert result is True

    def test_reset_singleton_by_key_invalid(self) -> None:
        """Test resetting an invalid singleton key."""
        result = reset_singleton_by_key("invalid_key")
        assert result is False

    def test_is_legacy_holder_key(self) -> None:
        """Test is_legacy_holder_key function."""
        # Container is now also legacy (uses contextvars)
        assert is_legacy_holder_key("container") is True

        # All these should be legacy
        for key in LEGACY_HOLDER_KEYS:
            assert is_legacy_holder_key(key) is True

        # Unknown keys are not legacy
        assert is_legacy_holder_key("unknown") is False

    def test_legacy_holder_keys_complete(self) -> None:
        """Test that LEGACY_HOLDER_KEYS contains all expected keys."""
        expected = {
            "action_registry",
            "command_registry",
            "event_type_registry",
            "logger_cache",
            "protocol_cache",
            "secret_manager",
            "container",  # Now also legacy (uses contextvars)
        }
        assert expected == LEGACY_HOLDER_KEYS

    def test_get_current_container_for_test(self) -> None:
        """Test get_current_container_for_test convenience function."""
        # Should return None when no container is set
        # First clear any existing container
        clear_all_caches()

        result = get_current_container_for_test()
        assert result is None

        # Set a container and verify it's returned
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]
        try:
            result = get_current_container_for_test()
            assert result is fake_container
        finally:
            _current_container.reset(token)


@pytest.mark.unit
class TestApplicationContext:
    """Tests for application context (contextvar) functionality."""

    def test_reset_application_context_basic(self) -> None:
        """Test that reset_application_context resets the contextvar to None."""
        # Set up a value in the contextvar
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]

        try:
            assert get_current_container() is fake_container

            # Reset the application context
            reset_application_context()

            # Should now be None
            assert get_current_container() is None
        finally:
            # Clean up
            _current_container.reset(token)

    def test_reset_application_context_idempotent(self) -> None:
        """Test that reset_application_context can be called multiple times."""
        # Multiple resets should be safe
        reset_application_context()
        reset_application_context()
        reset_application_context()
        assert get_current_container() is None

    def test_singleton_reset_context_resets_application_context(self) -> None:
        """Test that SingletonResetContext resets the application context."""
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]

        try:
            assert get_current_container() is fake_container

            with SingletonResetContext():
                # Inside context, application context should be None
                assert get_current_container() is None

            # After context, application context should be restored
            assert get_current_container() is fake_container
        finally:
            # Clean up
            _current_container.reset(token)

    def test_singleton_reset_context_restores_application_context(self) -> None:
        """Test that SingletonResetContext properly restores application context on exit."""
        original_container = FakeContainer()
        token = set_current_container(original_container)  # type: ignore[arg-type]

        try:
            with SingletonResetContext(holder_keys=["container"]):
                # Inside context, context should be None
                assert get_current_container() is None

            # After context, should be restored
            assert get_current_container() is original_container
        finally:
            # Clean up
            _current_container.reset(token)

    def test_clear_all_caches_resets_application_context(self) -> None:
        """Test that clear_all_caches also resets the application context."""
        fake_container = FakeContainer()
        token = set_current_container(fake_container)  # type: ignore[arg-type]

        try:
            assert get_current_container() is fake_container

            # clear_all_caches should reset the application context
            clear_all_caches()

            assert get_current_container() is None
        finally:
            # Clean up
            _current_container.reset(token)

    def test_reset_container_singleton_fixture_resets_context(
        self, reset_container_singleton: object
    ) -> None:
        """Test that reset_container_singleton fixture resets application context."""
        # Inside fixture, application context should be None
        assert get_current_container() is None

    def test_reset_all_singletons_fixture_resets_context(
        self, reset_all_singletons: object
    ) -> None:
        """Test that reset_all_singletons fixture resets application context."""
        # Inside fixture, application context should be None
        assert get_current_container() is None
