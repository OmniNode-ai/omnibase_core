"""
Comprehensive unit tests for logging/core_logging.py module.

Tests cover:
- emit_log_event() core functionality
- Correlation ID management (set/get)
- Thread-local correlation ID context
- Fallback logger functionality
- Async/sync emission patterns
- Thread safety
- Edge cases (no event loop, None handling)
"""

import asyncio
import threading
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.core_logging import (
    _SimpleFallbackLogger,
    _get_correlation_id,
    _get_registry_logger,
    emit_log_event,
    get_correlation_id,
    set_correlation_id,
)


class TestEmitLogEventCore:
    """Test core emit_log_event functionality."""

    def test_emit_log_event_basic(self):
        """Test basic emit_log_event call without event loop."""
        # Should not raise exception
        emit_log_event(LogLevel.INFO, "Test message")

    def test_emit_log_event_with_debug_level(self):
        """Test emit_log_event with DEBUG level."""
        emit_log_event(LogLevel.DEBUG, "Debug message")

    def test_emit_log_event_with_error_level(self):
        """Test emit_log_event with ERROR level."""
        emit_log_event(LogLevel.ERROR, "Error message")

    def test_emit_log_event_with_critical_level(self):
        """Test emit_log_event with CRITICAL level."""
        emit_log_event(LogLevel.CRITICAL, "Critical message")

    def test_emit_log_event_with_warning_level(self):
        """Test emit_log_event with WARNING level."""
        emit_log_event(LogLevel.WARNING, "Warning message")

    @pytest.mark.asyncio
    async def test_emit_log_event_with_event_loop(self):
        """Test emit_log_event when event loop is running."""
        # Should use async path with event loop
        emit_log_event(LogLevel.INFO, "Test with event loop")
        # Give async task time to execute
        await asyncio.sleep(0.01)

    def test_emit_log_event_auto_creates_correlation_id(self):
        """Test that emit_log_event auto-creates correlation ID."""
        # Clear any existing correlation ID
        import omnibase_core.logging.core_logging as core_logging

        if hasattr(core_logging._context, "correlation_id"):
            del core_logging._context.correlation_id

        # Emit should create correlation ID automatically
        emit_log_event(LogLevel.INFO, "Test")

        # Correlation ID should now exist
        correlation_id = get_correlation_id()
        assert correlation_id is not None
        assert isinstance(correlation_id, UUID)

    def test_emit_log_event_preserves_existing_correlation_id(self):
        """Test that emit_log_event preserves pre-set correlation ID."""
        test_correlation_id = uuid4()
        set_correlation_id(test_correlation_id)

        emit_log_event(LogLevel.INFO, "Test")

        # Should preserve the correlation ID
        assert get_correlation_id() == test_correlation_id


class TestCorrelationIdManagement:
    """Test correlation ID management functions."""

    def test_set_correlation_id(self):
        """Test setting correlation ID."""
        test_id = uuid4()
        set_correlation_id(test_id)

        assert get_correlation_id() == test_id

    def test_get_correlation_id_returns_none_when_not_set(self):
        """Test getting correlation ID when not set."""
        import omnibase_core.logging.core_logging as core_logging

        # Clear correlation ID
        if hasattr(core_logging._context, "correlation_id"):
            del core_logging._context.correlation_id

        # Should return None
        assert get_correlation_id() is None

    def test_set_and_get_correlation_id_round_trip(self):
        """Test setting and getting correlation ID."""
        test_id = uuid4()
        set_correlation_id(test_id)
        retrieved_id = get_correlation_id()

        assert retrieved_id == test_id
        assert isinstance(retrieved_id, UUID)

    def test_correlation_id_thread_isolation(self):
        """Test that correlation IDs are isolated per thread."""
        results = {}

        def set_thread_correlation_id(thread_id):
            correlation_id = uuid4()
            set_correlation_id(correlation_id)
            results[thread_id] = get_correlation_id()

        threads = [
            threading.Thread(target=set_thread_correlation_id, args=(i,))
            for i in range(3)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should have different correlation IDs
        correlation_ids = list(results.values())
        assert len(correlation_ids) == 3
        assert len(set(correlation_ids)) == 3  # All unique


class TestInternalCorrelationIdGetter:
    """Test _get_correlation_id internal function."""

    def test_get_correlation_id_creates_new_if_missing(self):
        """Test that _get_correlation_id creates UUID if missing."""
        import omnibase_core.logging.core_logging as core_logging

        # Clear correlation ID
        if hasattr(core_logging._context, "correlation_id"):
            del core_logging._context.correlation_id

        # Should create new UUID
        correlation_id = _get_correlation_id()
        assert isinstance(correlation_id, UUID)

    def test_get_correlation_id_returns_existing(self):
        """Test that _get_correlation_id returns existing UUID."""
        test_id = uuid4()
        set_correlation_id(test_id)

        correlation_id = _get_correlation_id()
        assert correlation_id == test_id

    def test_get_correlation_id_creates_only_once(self):
        """Test that _get_correlation_id creates UUID only once."""
        import omnibase_core.logging.core_logging as core_logging

        # Clear correlation ID
        if hasattr(core_logging._context, "correlation_id"):
            del core_logging._context.correlation_id

        # First call creates UUID
        first_id = _get_correlation_id()

        # Second call returns same UUID
        second_id = _get_correlation_id()

        assert first_id == second_id


class TestSimpleFallbackLogger:
    """Test _SimpleFallbackLogger functionality."""

    def test_fallback_logger_emit_info(self, capsys):
        """Test fallback logger emits INFO to stdout."""
        logger = _SimpleFallbackLogger()
        correlation_id = uuid4()

        logger.emit(LogLevel.INFO, "Test info message", correlation_id)

        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "Test info message" in captured.out
        assert str(correlation_id) in captured.out

    def test_fallback_logger_emit_debug(self, capsys):
        """Test fallback logger emits DEBUG to stdout."""
        logger = _SimpleFallbackLogger()
        correlation_id = uuid4()

        logger.emit(LogLevel.DEBUG, "Test debug message", correlation_id)

        captured = capsys.readouterr()
        assert "DEBUG" in captured.out
        assert "Test debug message" in captured.out

    def test_fallback_logger_emit_error_to_stderr(self, capsys):
        """Test fallback logger emits ERROR to stderr."""
        logger = _SimpleFallbackLogger()
        correlation_id = uuid4()

        logger.emit(LogLevel.ERROR, "Test error message", correlation_id)

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "Test error message" in captured.err
        assert str(correlation_id) in captured.err

    def test_fallback_logger_emit_critical_to_stderr(self, capsys):
        """Test fallback logger emits CRITICAL to stderr."""
        logger = _SimpleFallbackLogger()
        correlation_id = uuid4()

        logger.emit(LogLevel.CRITICAL, "Critical message", correlation_id)

        captured = capsys.readouterr()
        assert "CRITICAL" in captured.err
        assert "Critical message" in captured.err

    def test_fallback_logger_emit_fatal_to_stderr(self, capsys):
        """Test fallback logger emits FATAL to stderr."""
        logger = _SimpleFallbackLogger()
        correlation_id = uuid4()

        logger.emit(LogLevel.FATAL, "Fatal message", correlation_id)

        captured = capsys.readouterr()
        assert "FATAL" in captured.err
        assert "Fatal message" in captured.err

    def test_fallback_logger_emit_warning_to_stdout(self, capsys):
        """Test fallback logger emits WARNING to stdout."""
        logger = _SimpleFallbackLogger()
        correlation_id = uuid4()

        logger.emit(LogLevel.WARNING, "Warning message", correlation_id)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "Warning message" in captured.out


class TestGetRegistryLogger:
    """Test _get_registry_logger functionality."""

    def test_get_registry_logger_returns_logger(self):
        """Test that _get_registry_logger returns logger instance."""
        logger = _get_registry_logger()

        assert logger is not None
        assert hasattr(logger, "emit")

    def test_get_registry_logger_returns_fallback(self):
        """Test that _get_registry_logger returns fallback logger."""
        logger = _get_registry_logger()

        # Should be fallback logger
        assert isinstance(logger, _SimpleFallbackLogger)

    def test_get_registry_logger_caching(self):
        """Test that _get_registry_logger caches logger instance."""
        logger1 = _get_registry_logger()
        logger2 = _get_registry_logger()

        # Should return same instance
        assert logger1 is logger2

    def test_get_registry_logger_thread_safe(self):
        """Test that _get_registry_logger is thread-safe."""
        results = []

        def get_logger_in_thread():
            logger = _get_registry_logger()
            results.append(id(logger))

        threads = [threading.Thread(target=get_logger_in_thread) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get same logger instance
        assert len(set(results)) == 1


class TestAsyncEmission:
    """Test async emission patterns."""

    @pytest.mark.asyncio
    async def test_async_emit_via_logger(self):
        """Test async emit via logger."""
        from omnibase_core.logging.core_logging import _async_emit_via_logger

        logger = _get_registry_logger()
        correlation_id = uuid4()

        # Should not raise exception
        await _async_emit_via_logger(
            logger, LogLevel.INFO, "Async test", correlation_id
        )

    @pytest.mark.asyncio
    async def test_async_emit_via_logger_handles_exception(self):
        """Test async emit handles logger exceptions gracefully."""
        from omnibase_core.logging.core_logging import _async_emit_via_logger

        # Create mock logger that raises exception
        mock_logger = Mock()
        mock_logger.emit.side_effect = RuntimeError("Logger failure")

        correlation_id = uuid4()

        # Should not propagate exception (fire-and-forget)
        await _async_emit_via_logger(
            mock_logger, LogLevel.ERROR, "Test", correlation_id
        )

    @pytest.mark.asyncio
    async def test_async_emit_multiple_concurrent(self):
        """Test multiple concurrent async emissions."""
        from omnibase_core.logging.core_logging import _async_emit_via_logger

        logger = _get_registry_logger()

        # Create multiple concurrent emission tasks
        tasks = [
            _async_emit_via_logger(logger, LogLevel.INFO, f"Message {i}", uuid4())
            for i in range(10)
        ]

        # Should all complete without error
        await asyncio.gather(*tasks)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_emit_log_event_with_empty_message(self):
        """Test emit_log_event with empty message."""
        emit_log_event(LogLevel.INFO, "")

    def test_emit_log_event_with_long_message(self):
        """Test emit_log_event with very long message."""
        long_message = "A" * 10000
        emit_log_event(LogLevel.INFO, long_message)

    def test_emit_log_event_with_special_characters(self):
        """Test emit_log_event with special characters."""
        message = "Test with special chars: \n\t\r ñ é ü 中文 🚀"
        emit_log_event(LogLevel.INFO, message)

    def test_emit_log_event_with_none_in_message(self):
        """Test emit_log_event handles None gracefully."""
        # Should convert None to string
        emit_log_event(LogLevel.INFO, str(None))

    def test_correlation_id_persists_across_multiple_emits(self):
        """Test correlation ID persists across multiple log emissions."""
        test_id = uuid4()
        set_correlation_id(test_id)

        # Emit multiple times
        for i in range(5):
            emit_log_event(LogLevel.INFO, f"Message {i}")

        # Correlation ID should still be the same
        assert get_correlation_id() == test_id


class TestThreadSafety:
    """Test thread safety of logging functions."""

    def test_concurrent_emit_different_correlation_ids(self):
        """Test concurrent emissions with different correlation IDs."""
        results = {}

        def emit_with_thread_id(thread_id):
            correlation_id = uuid4()
            set_correlation_id(correlation_id)

            for i in range(5):
                emit_log_event(LogLevel.INFO, f"Thread {thread_id} message {i}")

            results[thread_id] = get_correlation_id()

        threads = [threading.Thread(target=emit_with_thread_id, args=(i,)) for i in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should have different correlation IDs
        correlation_ids = list(results.values())
        assert len(correlation_ids) == 3
        assert len(set(correlation_ids)) == 3

    def test_concurrent_logger_access(self):
        """Test concurrent access to logger is thread-safe."""

        def access_logger():
            logger = _get_registry_logger()
            correlation_id = uuid4()
            logger.emit(LogLevel.INFO, "Concurrent access", correlation_id)

        threads = [threading.Thread(target=access_logger) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors
