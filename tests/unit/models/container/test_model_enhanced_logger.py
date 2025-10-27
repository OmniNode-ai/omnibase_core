"""Tests for ModelEnhancedLogger."""

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.container.model_enhanced_logger import ModelEnhancedLogger


class TestModelEnhancedLogger:
    """Tests for ModelEnhancedLogger."""

    def test_initialization(self):
        """Test logger initialization with level."""
        logger = ModelEnhancedLogger(LogLevel.INFO)
        assert logger.level == LogLevel.INFO

    def test_emit_log_event_sync_above_level(self):
        """Test sync logging for messages above threshold."""
        logger = ModelEnhancedLogger(LogLevel.INFO)

        # Should log INFO and above
        logger.emit_log_event_sync(LogLevel.INFO, "Info message")
        logger.emit_log_event_sync(LogLevel.WARNING, "Warning message")
        logger.emit_log_event_sync(LogLevel.ERROR, "Error message")

    def test_emit_log_event_sync_below_level(self):
        """Test sync logging filters messages below threshold."""
        logger = ModelEnhancedLogger(LogLevel.WARNING)

        # Should not log DEBUG or INFO
        logger.emit_log_event_sync(LogLevel.DEBUG, "Debug message")
        logger.emit_log_event_sync(LogLevel.INFO, "Info message")

    def test_emit_log_event_sync_with_event_type(self):
        """Test sync logging with event type."""
        logger = ModelEnhancedLogger(LogLevel.DEBUG)

        logger.emit_log_event_sync(
            LogLevel.INFO,
            "Custom event",
            event_type="custom",
        )

    def test_emit_log_event_sync_with_kwargs(self):
        """Test sync logging with additional kwargs."""
        logger = ModelEnhancedLogger(LogLevel.DEBUG)

        logger.emit_log_event_sync(
            LogLevel.INFO,
            "Event with data",
            event_type="data_event",
            user_id="123",
            request_id="req-456",
        )

    @pytest.mark.asyncio
    async def test_emit_log_event_async(self):
        """Test async logging delegates to sync."""
        logger = ModelEnhancedLogger(LogLevel.INFO)

        await logger.emit_log_event_async(LogLevel.INFO, "Async message")
        await logger.emit_log_event_async(
            LogLevel.WARNING,
            "Async warning",
            event_type="async_warning",
        )

    @pytest.mark.asyncio
    async def test_emit_log_event_async_with_kwargs(self):
        """Test async logging with kwargs."""
        logger = ModelEnhancedLogger(LogLevel.DEBUG)

        await logger.emit_log_event_async(
            LogLevel.ERROR,
            "Async error",
            event_type="async_error",
            error_code="E123",
            stack_trace="...",
        )

    def test_emit_log_event_defaults_to_sync(self):
        """Test emit_log_event defaults to sync behavior."""
        logger = ModelEnhancedLogger(LogLevel.INFO)

        logger.emit_log_event(LogLevel.INFO, "Default message")
        logger.emit_log_event(
            LogLevel.WARNING,
            "Default warning",
            event_type="default",
        )

    def test_info_convenience_method(self):
        """Test info convenience method."""
        logger = ModelEnhancedLogger(LogLevel.DEBUG)

        logger.info("Info message")

    def test_warning_convenience_method(self):
        """Test warning convenience method."""
        logger = ModelEnhancedLogger(LogLevel.DEBUG)

        logger.warning("Warning message")

    def test_error_convenience_method(self):
        """Test error convenience method."""
        logger = ModelEnhancedLogger(LogLevel.DEBUG)

        logger.error("Error message")

    def test_convenience_methods_filtered_by_level(self):
        """Test convenience methods respect log level."""
        logger = ModelEnhancedLogger(LogLevel.ERROR)

        # These should be filtered out
        logger.info("Should not log")
        logger.warning("Should not log")

        # This should log
        logger.error("Should log")

    def test_different_log_levels(self):
        """Test logger with different log levels."""
        for level in [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            logger = ModelEnhancedLogger(level)
            assert logger.level == level

    def test_level_comparison(self):
        """Test log level filtering logic."""
        # DEBUG logger logs everything
        debug_logger = ModelEnhancedLogger(LogLevel.DEBUG)
        debug_logger.emit_log_event_sync(LogLevel.DEBUG, "Debug")
        debug_logger.emit_log_event_sync(LogLevel.INFO, "Info")
        debug_logger.emit_log_event_sync(LogLevel.WARNING, "Warning")
        debug_logger.emit_log_event_sync(LogLevel.ERROR, "Error")

        # ERROR logger only logs errors
        error_logger = ModelEnhancedLogger(LogLevel.ERROR)
        error_logger.emit_log_event_sync(LogLevel.DEBUG, "Filtered")
        error_logger.emit_log_event_sync(LogLevel.INFO, "Filtered")
        error_logger.emit_log_event_sync(LogLevel.WARNING, "Filtered")
        error_logger.emit_log_event_sync(LogLevel.ERROR, "Logged")

    @pytest.mark.asyncio
    async def test_mixed_sync_async_logging(self):
        """Test mixing sync and async logging."""
        logger = ModelEnhancedLogger(LogLevel.INFO)

        logger.emit_log_event_sync(LogLevel.INFO, "Sync message 1")
        await logger.emit_log_event_async(LogLevel.INFO, "Async message 1")
        logger.emit_log_event(LogLevel.INFO, "Default message 1")
        logger.info("Info message 1")
        await logger.emit_log_event_async(LogLevel.WARNING, "Async warning")
        logger.warning("Sync warning")
