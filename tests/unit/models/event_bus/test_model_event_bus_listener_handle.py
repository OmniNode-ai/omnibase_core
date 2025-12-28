# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ModelEventBusListenerHandle.

Comprehensive tests for event bus listener handle lifecycle management,
including thread management, stop signals, and subscription tracking.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_event_bus_listener_handle import (
    ModelEventBusListenerHandle,
)


@pytest.mark.unit
class TestModelEventBusListenerHandleInitialization:
    """Test ModelEventBusListenerHandle initialization."""

    def test_create_default_handle(self) -> None:
        """Test creating a handle with default values."""
        handle = ModelEventBusListenerHandle()

        assert handle is not None
        assert isinstance(handle, ModelEventBusListenerHandle)
        assert handle.listener_thread is None
        assert handle.stop_event is None
        assert handle.subscriptions == []
        assert handle.is_running is False

    def test_create_handle_with_values(self) -> None:
        """Test creating a handle with explicit values."""
        thread = threading.Thread(target=lambda: None, daemon=True)
        stop_event = threading.Event()
        subscriptions = ["sub1", "sub2"]

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            stop_event=stop_event,
            subscriptions=subscriptions,
            is_running=True,
        )

        assert handle.listener_thread is thread
        assert handle.stop_event is stop_event
        assert handle.subscriptions == subscriptions
        assert handle.is_running is True


@pytest.mark.unit
class TestModelEventBusListenerHandleStopIdempotent:
    """Test ModelEventBusListenerHandle.stop() idempotency."""

    def test_stop_is_idempotent_when_already_stopped(self) -> None:
        """Test stop() is idempotent - calling multiple times is safe."""
        handle = ModelEventBusListenerHandle(
            is_running=False,
            listener_thread=None,
        )

        # Call stop multiple times
        result1 = handle.stop()
        result2 = handle.stop()
        result3 = handle.stop()

        assert result1 is True
        assert result2 is True
        assert result3 is True

    def test_stop_returns_true_when_already_stopped(self) -> None:
        """Test stop() returns True when listener is already stopped."""
        handle = ModelEventBusListenerHandle(
            is_running=False,
            listener_thread=None,
        )

        result = handle.stop()

        assert result is True

    def test_stop_returns_true_for_default_handle(self) -> None:
        """Test stop() returns True for default (never started) handle."""
        handle = ModelEventBusListenerHandle()

        result = handle.stop()

        assert result is True


@pytest.mark.unit
class TestModelEventBusListenerHandleStopSignaling:
    """Test ModelEventBusListenerHandle.stop() signal behavior."""

    def test_stop_signals_stop_event(self) -> None:
        """Test stop() sets the stop_event."""
        stop_event = threading.Event()
        handle = ModelEventBusListenerHandle(
            stop_event=stop_event,
            is_running=True,
        )

        assert not stop_event.is_set()

        handle.stop(timeout=0.1)

        assert stop_event.is_set()

    def test_stop_with_none_stop_event(self) -> None:
        """Test stop() handles None stop_event gracefully."""
        handle = ModelEventBusListenerHandle(
            stop_event=None,
            is_running=True,
        )

        # Should not raise an error
        result = handle.stop(timeout=0.1)

        # Will return True since there's no thread to wait for
        assert handle.is_running is False


@pytest.mark.unit
class TestModelEventBusListenerHandleStopClearsSubscriptions:
    """Test ModelEventBusListenerHandle.stop() clears subscriptions."""

    def test_stop_clears_subscriptions(self) -> None:
        """Test stop() clears subscriptions list."""
        subscriptions = ["sub1", "sub2", "sub3"]
        handle = ModelEventBusListenerHandle(
            subscriptions=subscriptions.copy(),
            is_running=True,
        )

        assert len(handle.subscriptions) == 3

        handle.stop(timeout=0.1)

        assert len(handle.subscriptions) == 0

    def test_stop_clears_subscriptions_even_on_timeout(self) -> None:
        """Test stop() clears subscriptions even if thread doesn't stop."""

        def never_stopping_target() -> None:
            while True:
                time.sleep(0.1)

        thread = threading.Thread(target=never_stopping_target, daemon=True)
        thread.start()

        subscriptions = ["sub1", "sub2"]
        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            subscriptions=subscriptions.copy(),
            is_running=True,
        )

        # Use very short timeout
        result = handle.stop(timeout=0.01)

        # Subscriptions should be cleared regardless
        assert len(handle.subscriptions) == 0


@pytest.mark.unit
class TestModelEventBusListenerHandleStopSetsIsRunning:
    """Test ModelEventBusListenerHandle.stop() sets is_running to False."""

    def test_stop_sets_is_running_to_false(self) -> None:
        """Test stop() sets is_running to False."""
        handle = ModelEventBusListenerHandle(
            is_running=True,
        )

        assert handle.is_running is True

        handle.stop(timeout=0.1)

        assert handle.is_running is False

    def test_stop_sets_is_running_false_even_on_timeout(self) -> None:
        """Test stop() sets is_running to False even when thread doesn't stop."""

        def never_stopping_target() -> None:
            while True:
                time.sleep(0.1)

        thread = threading.Thread(target=never_stopping_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,
        )

        # Use very short timeout
        handle.stop(timeout=0.01)

        # is_running should be False regardless
        assert handle.is_running is False


@pytest.mark.unit
class TestModelEventBusListenerHandleIsActive:
    """Test ModelEventBusListenerHandle.is_active() method."""

    def test_is_active_returns_false_when_no_thread(self) -> None:
        """Test is_active() returns False when listener_thread is None."""
        handle = ModelEventBusListenerHandle(
            listener_thread=None,
        )

        assert handle.is_active() is False

    def test_is_active_returns_true_for_alive_thread(self) -> None:
        """Test is_active() returns True when thread is alive."""
        stop_event = threading.Event()

        def thread_target() -> None:
            stop_event.wait()

        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            stop_event=stop_event,
            is_running=True,
        )

        try:
            assert handle.is_active() is True
        finally:
            stop_event.set()
            thread.join(timeout=1.0)

    def test_is_active_returns_false_for_finished_thread(self) -> None:
        """Test is_active() returns False when thread has finished."""

        def quick_target() -> None:
            pass

        thread = threading.Thread(target=quick_target, daemon=True)
        thread.start()
        thread.join(timeout=1.0)

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,  # Note: is_running may still be True
        )

        # Thread is finished, so is_active should be False
        assert handle.is_active() is False

    def test_is_active_vs_is_running_discrepancy(self) -> None:
        """Test that is_active() checks actual thread state, not is_running flag."""

        def quick_target() -> None:
            pass

        thread = threading.Thread(target=quick_target, daemon=True)
        thread.start()
        thread.join(timeout=1.0)

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,  # Flag says running
        )

        # is_running is True but thread is actually dead
        assert handle.is_running is True
        assert handle.is_active() is False


@pytest.mark.unit
class TestModelEventBusListenerHandleStopWithRealThread:
    """Test ModelEventBusListenerHandle.stop() with real threading scenarios."""

    def test_stop_with_cooperating_thread(self) -> None:
        """Test stop() with a thread that respects the stop event."""
        stop_event = threading.Event()

        def cooperating_target() -> None:
            while not stop_event.is_set():
                time.sleep(0.01)

        thread = threading.Thread(target=cooperating_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            stop_event=stop_event,
            is_running=True,
        )

        result = handle.stop(timeout=5.0)

        assert result is True
        assert handle.is_running is False
        assert not thread.is_alive()

    def test_stop_with_non_cooperating_thread_logs_warning(self) -> None:
        """Test stop() logs warning when thread doesn't stop within timeout."""

        def never_stopping_target() -> None:
            while True:
                time.sleep(0.1)

        thread = threading.Thread(target=never_stopping_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,
        )

        with patch(
            "omnibase_core.models.event_bus.model_event_bus_listener_handle.emit_log_event"
        ) as mock_log:
            result = handle.stop(timeout=0.01)

            assert result is False
            assert handle.is_running is False
            # Verify warning was logged
            mock_log.assert_called_once()
            # Check the log level was WARNING
            from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

            call_args = mock_log.call_args
            assert call_args[0][0] == LogLevel.WARNING

    def test_stop_respects_custom_timeout(self) -> None:
        """Test stop() respects custom timeout parameter."""

        def slow_stopping_target() -> None:
            time.sleep(0.2)

        thread = threading.Thread(target=slow_stopping_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,
        )

        start_time = time.time()
        # With short timeout, should return quickly
        handle.stop(timeout=0.01)
        elapsed = time.time() - start_time

        # Should have returned quickly due to timeout
        assert elapsed < 0.1


@pytest.mark.unit
class TestModelEventBusListenerHandleStopReturnValue:
    """Test ModelEventBusListenerHandle.stop() return value semantics."""

    def test_stop_returns_true_when_thread_stops_in_time(self) -> None:
        """Test stop() returns True when thread stops within timeout."""
        stop_event = threading.Event()

        def quick_target() -> None:
            stop_event.wait(timeout=0.5)

        thread = threading.Thread(target=quick_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            stop_event=stop_event,
            is_running=True,
        )

        result = handle.stop(timeout=5.0)

        assert result is True

    def test_stop_returns_false_when_thread_does_not_stop(self) -> None:
        """Test stop() returns False when thread doesn't stop in time."""

        def infinite_target() -> None:
            while True:
                time.sleep(0.1)

        thread = threading.Thread(target=infinite_target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,
        )

        result = handle.stop(timeout=0.01)

        assert result is False


@pytest.mark.unit
class TestModelEventBusListenerHandleModelConfig:
    """Test ModelEventBusListenerHandle model configuration."""

    def test_model_is_mutable(self) -> None:
        """Test that the model is mutable (frozen=False)."""
        handle = ModelEventBusListenerHandle(is_running=False)

        handle.is_running = True

        assert handle.is_running is True

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusListenerHandle(
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

        assert "extra_field" in str(exc_info.value)

    def test_model_allows_arbitrary_types(self) -> None:
        """Test that model allows arbitrary types (threading objects)."""
        thread = threading.Thread(target=lambda: None, daemon=True)
        event = threading.Event()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            stop_event=event,
        )

        assert handle.listener_thread is thread
        assert handle.stop_event is event


@pytest.mark.unit
class TestModelEventBusListenerHandleSerialization:
    """Test ModelEventBusListenerHandle serialization behavior."""

    def test_fields_excluded_from_serialization(self) -> None:
        """Test that all fields are excluded from serialization."""
        thread = threading.Thread(target=lambda: None, daemon=True)
        stop_event = threading.Event()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            stop_event=stop_event,
            subscriptions=["sub1", "sub2"],
            is_running=True,
        )

        data = handle.model_dump()

        # All fields should be excluded
        assert "listener_thread" not in data
        assert "stop_event" not in data
        assert "subscriptions" not in data
        assert "is_running" not in data
        assert data == {}

    def test_json_serialization_returns_empty(self) -> None:
        """Test JSON serialization returns empty object."""
        handle = ModelEventBusListenerHandle(
            subscriptions=["sub1"],
            is_running=True,
        )

        json_data = handle.model_dump_json()

        assert json_data == "{}"


@pytest.mark.unit
class TestModelEventBusListenerHandleSubscriptions:
    """Test ModelEventBusListenerHandle subscription management."""

    def test_subscriptions_default_to_empty_list(self) -> None:
        """Test subscriptions default to empty list."""
        handle = ModelEventBusListenerHandle()

        assert handle.subscriptions == []
        assert isinstance(handle.subscriptions, list)

    def test_subscriptions_can_hold_any_type(self) -> None:
        """Test subscriptions list can hold any type (list[Any])."""
        mock_sub1 = MagicMock()
        mock_sub2 = {"topic": "test"}

        handle = ModelEventBusListenerHandle(
            subscriptions=[mock_sub1, mock_sub2, 123, "string_sub"],
        )

        assert len(handle.subscriptions) == 4
        assert mock_sub1 in handle.subscriptions
        assert mock_sub2 in handle.subscriptions

    def test_subscriptions_can_be_modified(self) -> None:
        """Test subscriptions list can be modified."""
        handle = ModelEventBusListenerHandle()

        handle.subscriptions.append("new_sub")

        assert len(handle.subscriptions) == 1
        assert "new_sub" in handle.subscriptions


@pytest.mark.unit
class TestModelEventBusListenerHandleEdgeCases:
    """Test ModelEventBusListenerHandle edge cases."""

    def test_stop_with_dead_thread_and_running_true(self) -> None:
        """Test stop() when thread is dead but is_running is True."""

        def quick_target() -> None:
            pass

        thread = threading.Thread(target=quick_target, daemon=True)
        thread.start()
        thread.join(timeout=1.0)

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,
        )

        # Thread is dead, is_running is True
        result = handle.stop()

        # Should return True since thread is not alive
        assert result is True
        assert handle.is_running is False

    def test_stop_with_zero_timeout(self) -> None:
        """Test stop() with zero timeout."""

        def target() -> None:
            time.sleep(0.1)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        handle = ModelEventBusListenerHandle(
            listener_thread=thread,
            is_running=True,
        )

        # Zero timeout should return immediately
        result = handle.stop(timeout=0.0)

        # Thread might still be alive
        assert handle.is_running is False

    def test_model_copy_creates_independent_subscriptions(self) -> None:
        """Test that model_copy creates independent subscriptions list."""
        original = ModelEventBusListenerHandle(
            subscriptions=["sub1", "sub2"],
        )

        # Use deep=True to get independent subscriptions list
        copied = original.model_copy(deep=True)

        copied.subscriptions.append("sub3")

        assert len(original.subscriptions) == 2
        assert len(copied.subscriptions) == 3
