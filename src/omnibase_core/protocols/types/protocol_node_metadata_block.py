"""
ProtocolNodeMetadataBlock - Protocol for node metadata blocks.

This module provides the protocol definition for node metadata block objects.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import ProtocolDateTime, ProtocolSemVer


@runtime_checkable
class ProtocolNodeMetadataBlock(Protocol):
    """
    Protocol for node metadata block objects.

    Defines the structure of ONEX node metadata including identification,
    versioning, and lifecycle information.
    """

    uuid: UUID
    name: str
    description: str
    version: ProtocolSemVer
    metadata_version: ProtocolSemVer
    namespace: str
    created_at: ProtocolDateTime
    last_modified_at: ProtocolDateTime
    lifecycle: str
    protocol_version: ProtocolSemVer

    async def validate_metadata_block(self) -> bool:
        """Validate the metadata block."""
        ...

    def is_complete(self) -> bool:
        """Check if the metadata block is complete."""
        ...


__all__ = ["ProtocolNodeMetadataBlock"]
