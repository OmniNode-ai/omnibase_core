"""
ProtocolMinimalLogger - Protocol for minimal bootstrap logging.

This module provides the protocol definition for minimal loggers
used during bootstrap phase when full logging infrastructure is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from omnibase_core.enums.enum_log_level import EnumLogLevel


@runtime_checkable
class ProtocolMinimalLogger(Protocol):
    """
    Protocol for minimal bootstrap loggers.

    Provides basic logging interface for bootstrap scenarios
    when full logging infrastructure is unavailable.
    """

    def emit_log_event(
        self,
        level: EnumLogLevel,
        event_type: str,
        message: str,
        **kwargs: object,
    ) -> None:
        """Emit a structured log event."""
        ...

    def emit_log_event_sync(
        self,
        level: EnumLogLevel,
        message: str,
        event_type: str = ...,
        **kwargs: object,
    ) -> None:
        """Synchronous log event emission."""
        ...

    async def emit_log_event_async(
        self,
        level: EnumLogLevel,
        message: str,
        event_type: str = ...,
        **kwargs: object,
    ) -> None:
        """Asynchronous log event emission."""
        ...

    def trace_function_lifecycle[F: Callable[..., object]](self, func: F) -> F:
        """Decorator to trace function lifecycle."""
        ...

    def tool_logger_performance_metrics(
        self,
        _threshold_ms: int = ...,
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Decorator for performance metrics logging."""
        ...


__all__ = ["ProtocolMinimalLogger"]
