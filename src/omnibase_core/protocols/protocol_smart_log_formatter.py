"""
Protocol for smart log formatting.

This module provides the ProtocolSmartLogFormatter protocol which defines
the interface for logging formatters used in the ONEX logging infrastructure.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- NO Any types - use structured types for log data
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.enum_log_level import EnumLogLevel
    from omnibase_core.models.core.model_log_context import ModelLogContext

# Type alias for log data values - JSON-compatible types
LogDataValue = str | int | float | bool | None


@runtime_checkable
class ProtocolSmartLogFormatter(Protocol):
    """
    Protocol for smart log formatting.

    Defines the interface for logging formatters that convert structured
    log events into formatted output strings. Used by the ONEX logging
    infrastructure for consistent log formatting across the platform.

    The formatter is responsible for:
    - Converting log events to human-readable format
    - Including context information (module, function, line)
    - Formatting structured data as JSON or key-value pairs
    - Applying appropriate formatting based on log level

    Example:
        class MyLogFormatter:
            def format_log_event(
                self,
                level: EnumLogLevel,
                event_type: str,
                message: str,
                context: ModelLogContext,
                data: dict[str, LogDataValue],
                correlation_id: str,
            ) -> str:
                return f"[{level.name}] {correlation_id}: {message}"
    """

    def format_log_event(
        self,
        level: EnumLogLevel,
        event_type: str,
        message: str,
        context: ModelLogContext,
        data: dict[str, LogDataValue],
        correlation_id: str,
    ) -> str:
        """
        Format a structured log event into a string.

        Args:
            level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
            event_type: Type of event (function_entry, node_execution_start, etc.)
            message: Primary log message
            context: Log context with calling module, function, line, timestamp
            data: Additional structured data as key-value pairs
            correlation_id: Correlation ID for tracing (as string)

        Returns:
            Formatted log string ready for output
        """
        ...


__all__ = ["ProtocolSmartLogFormatter", "LogDataValue"]
