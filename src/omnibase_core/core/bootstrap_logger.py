"""
Bootstrap Logger

Basic logger implementation for container initialization before
full logging infrastructure is available.
"""

from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.protocol.protocol_logger import ProtocolLogger


def create_basic_logger(level: LogLevelEnum = LogLevelEnum.INFO) -> ProtocolLogger:
    """Create basic logger for bootstrap."""

    class BasicLogger:
        def __init__(self, level: LogLevelEnum) -> None:
            self.level = level

        def emit_log_event_sync(
            self,
            level: LogLevelEnum,
            message: str,
            event_type: str = "generic",
            **kwargs: object,
        ) -> None:
            """Emit log event synchronously."""
            if level.value >= self.level.value:
                print(f"[{level.name}] {message}")

        async def emit_log_event_async(
            self,
            level: LogLevelEnum,
            message: str,
            event_type: str = "generic",
            **kwargs: object,
        ) -> None:
            """Emit log event asynchronously."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def emit_log_event(
            self,
            level: LogLevelEnum,
            message: str,
            event_type: str = "generic",
            **kwargs: object,
        ) -> None:
            """Emit log event (defaults to sync)."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def info(self, message: str) -> None:
            """Info level logging for compatibility."""
            self.emit_log_event_sync(LogLevelEnum.INFO, message, "info")

        def warning(self, message: str) -> None:
            """Warning level logging for compatibility."""
            self.emit_log_event_sync(LogLevelEnum.WARNING, message, "warning")

        def error(self, message: str) -> None:
            """Error level logging for compatibility."""
            self.emit_log_event_sync(LogLevelEnum.ERROR, message, "error")

    return BasicLogger(level)
