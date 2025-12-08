"""
ProtocolAction - Protocol for reducer actions.

This module provides the protocol definition for action objects used in
reducer dispatch operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ProtocolDateTime


@runtime_checkable
class ProtocolAction(Protocol):
    """
    Protocol for reducer actions.

    Defines the interface for action objects used in reducer dispatch operations.
    """

    type: str
    payload: object | None
    timestamp: ProtocolDateTime

    async def validate_action(self) -> bool:
        """Validate action structure and payload."""
        ...

    def is_executable(self) -> bool:
        """Check if action can be executed."""
        ...


__all__ = ["ProtocolAction"]
