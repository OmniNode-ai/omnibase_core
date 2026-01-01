"""
ProtocolSmartLogFormatter - Protocol for smart log event formatting.

This module provides the protocol definition for log formatters that
transform structured log events into formatted output strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.enum_log_level import EnumLogLevel
    from omnibase_core.models.core.model_log_context import ModelLogContext

# Type alias for log data values - JSON-compatible types
# Consistent with omnibase_core.protocols.protocol_smart_log_formatter.LogDataValue
LogDataValue = str | int | float | bool | None


@runtime_checkable
class ProtocolSmartLogFormatter(Protocol):
    """
    Protocol for smart log event formatters.

    Transforms structured log events into formatted output strings
    suitable for display or storage.
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
        Format a log event into a string representation.

        Args:
            level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
            event_type: Type of event (function_entry, node_execution_start, etc.)
            message: Primary log message
            context: Log context with calling function, module, and line info
            data: Additional structured data
            correlation_id: Correlation ID for tracing

        Returns:
            Formatted log string
        """
        ...


__all__ = ["ProtocolSmartLogFormatter", "LogDataValue"]
