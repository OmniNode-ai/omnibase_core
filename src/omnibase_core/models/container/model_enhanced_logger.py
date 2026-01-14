"""
ModelEnhancedLogger

Enhanced logger with monadic patterns for dependency injection container.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


class ModelEnhancedLogger:
    """Enhanced logger with monadic patterns."""

    def __init__(self, level: LogLevel):
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
            from datetime import UTC, datetime

            timestamp = datetime.now(UTC).isoformat()
            # print-ok: stub logger output - this is intentional for minimal logging
            print(f"[{timestamp}] [{level.name}] [{event_type}] {message}")

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
        self.emit_log_event_sync(LogLevel.INFO, message, "info")

    def warning(self, message: str) -> None:
        self.emit_log_event_sync(LogLevel.WARNING, message, "warning")

    def error(self, message: str) -> None:
        self.emit_log_event_sync(LogLevel.ERROR, message, "error")
