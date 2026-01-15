"""
Protocol for structured log emission via event bus.

This module provides the ProtocolEventBusLogEmitter protocol definition
for structured log event emission.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.enums import EnumLogLevel


@runtime_checkable
class ProtocolEventBusLogEmitter(Protocol):
    """
    Protocol for structured log emission via event bus.

    Defines interface for components that can emit structured
    log events with typed data and log levels.
    """

    def emit_log_event(
        self,
        level: EnumLogLevel,
        message: str,
        data: dict[str, str | int | float | bool],
    ) -> None:
        """Emit a structured log event."""
        ...


__all__ = ["ProtocolEventBusLogEmitter"]
