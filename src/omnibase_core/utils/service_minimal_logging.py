from __future__ import annotations

"""
ServiceMinimalLogging

Minimal logging service for bootstrap scenarios.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


from typing import Any

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


class ServiceMinimalLogging:
    """Minimal logging service for bootstrap scenarios."""

    @staticmethod
    def emit_log_event(  # stub-ok: Minimal logging service provides pass-through implementation
        level: LogLevel,
        event_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Minimal log event implementation."""

    @staticmethod
    def emit_log_event_sync(  # stub-ok: Minimal logging service provides pass-through implementation
        level: LogLevel,
        message: str,
        event_type: str = "generic",
        **kwargs: Any,
    ) -> None:
        """Minimal synchronous log event implementation."""

    @staticmethod
    async def emit_log_event_async(  # stub-ok: Minimal logging service provides pass-through implementation
        level: LogLevel,
        message: str,
        event_type: str = "generic",
        **kwargs: Any,
    ) -> None:
        """Minimal asynchronous log event implementation."""

    @staticmethod
    def trace_function_lifecycle(func: Any) -> Any:
        """No-op decorator for bootstrap."""
        return func

    @staticmethod
    def tool_logger_performance_metrics(_threshold_ms: int = 1000) -> Any:
        """Minimal tool logger performance metrics decorator."""

        def decorator(func: Any) -> Any:
            return func

        return decorator
