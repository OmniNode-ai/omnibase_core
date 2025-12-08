"""
ProtocolState - Protocol for reducer state.

This module provides the protocol definition for state objects used in
reducer nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnibase_core.protocols.base import ProtocolDateTime

if TYPE_CHECKING:
    from omnibase_core.protocols.types.protocol_metadata import ProtocolMetadata


@runtime_checkable
class ProtocolState(Protocol):
    """
    Protocol for reducer state.

    Defines the interface for state objects used in reducer nodes.
    """

    metadata: ProtocolMetadata
    version: int
    last_updated: ProtocolDateTime

    async def validate_state(self) -> bool:
        """Validate the state."""
        ...

    def is_consistent(self) -> bool:
        """Check if the state is consistent."""
        ...


__all__ = ["ProtocolState"]
