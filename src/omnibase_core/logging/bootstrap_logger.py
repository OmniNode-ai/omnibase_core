"""
Bootstrap Logger

Basic logger implementation for container initialization before
full logging infrastructure is available.
"""

from typing import Any

from omnibase_spi import ProtocolLogger

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


def create_basic_logger(level: LogLevel = LogLevel.INFO) -> ProtocolLogger:
    """Create basic logger for bootstrap."""

    class BasicLogger:
        def __init__(self, level: LogLevel) -> None:
            self.level = level

        def emit_log_event_sync(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: object,
        ) -> None:
            """Emit log event synchronously."""
            if level.value >= self.level.value:
                pass

        async def emit_log_event_async(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: object,
        ) -> None:
            """Emit log event asynchronously."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def emit_log_event(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: object,
        ) -> None:
            """Emit log event (defaults to sync)."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def info(self, message: str) -> None:
            """Info level logging for current standards."""
            self.emit_log_event_sync(LogLevel.INFO, message, "info")

        def warning(self, message: str) -> None:
            """Warning level logging for current standards."""
            self.emit_log_event_sync(LogLevel.WARNING, message, "warning")

        def error(self, message: str) -> None:
            """Error level logging for current standards."""
            self.emit_log_event_sync(LogLevel.ERROR, message, "error")

    return BasicLogger(level)
