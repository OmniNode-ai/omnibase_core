from __future__ import annotations

"""
ServiceLogging

Registry-based logging service implementation.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


from typing import Any


class ServiceLogging:
    """Registry-based logging service implementation."""

    def __init__(self, protocol: Any) -> None:
        """Initialize with logger protocol."""
        self._protocol = protocol

    def emit_log_event(self, *args: Any, **kwargs: Any) -> Any:
        """Emit log event via protocol."""
        return self._protocol.emit_log_event(*args, **kwargs)

    def emit_log_event_sync(self, *args: Any, **kwargs: Any) -> Any:
        """Emit log event synchronously via protocol."""
        return self._protocol.emit_log_event_sync(*args, **kwargs)

    def emit_log_event_async(self, *args: Any, **kwargs: Any) -> Any:
        """Emit log event asynchronously via protocol."""
        return self._protocol.emit_log_event_async(*args, **kwargs)

    def trace_function_lifecycle(self, func: Any) -> Any:
        """Trace function lifecycle via protocol."""
        return self._protocol.trace_function_lifecycle(func)

    @property
    def ToolLoggerCodeBlock(self) -> Any:
        """Get ToolLoggerCodeBlock via protocol."""
        return self._protocol.ToolLoggerCodeBlock

    def tool_logger_performance_metrics(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Get tool logger performance metrics via protocol."""
        return self._protocol.tool_logger_performance_metrics(
            *args,
            **kwargs,
        )
