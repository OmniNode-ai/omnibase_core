"""
ProtocolNodeMetadata - Protocol for node metadata.

This module provides the protocol definition for ONEX node metadata objects.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolNodeMetadata(Protocol):
    """
    Protocol for ONEX node metadata objects.

    Defines the essential metadata structure for nodes in the ONEX
    distributed system.
    """

    node_id: UUID
    node_type: str
    metadata: dict[str, ContextValue]

    async def validate_node_metadata(self) -> bool:
        """Validate the node metadata."""
        ...

    def is_complete(self) -> bool:
        """Check if the metadata is complete."""
        ...


__all__ = ["ProtocolNodeMetadata"]
