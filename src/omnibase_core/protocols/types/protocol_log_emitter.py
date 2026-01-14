"""
ProtocolLogEmitter - Protocol for log emitters.

This module provides the protocol definition for objects that can emit
structured log events.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.enums import EnumLogLevel


@runtime_checkable
class ProtocolLogEmitter(Protocol):
    """
    Protocol for objects that can emit structured log events.

    Provides standardized logging interface for ONEX services.
    """

    def emit_log_event(
        self,
        level: EnumLogLevel,
        message: str,
        data: object,
    ) -> None:
        """Emit a structured log event."""
        ...


__all__ = ["ProtocolLogEmitter"]
