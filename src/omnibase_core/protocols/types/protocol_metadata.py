"""
ProtocolMetadata - Protocol for structured metadata.

This module provides the protocol definition for structured metadata objects.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue, ProtocolDateTime, ProtocolSemVer


@runtime_checkable
class ProtocolMetadata(Protocol):
    """
    Protocol for structured metadata.

    Attribute-based for data compatibility.
    """

    data: dict[str, ContextValue]
    version: ProtocolSemVer
    created_at: ProtocolDateTime
    updated_at: ProtocolDateTime | None

    async def validate_metadata(self) -> bool:
        """Validate the metadata."""
        ...

    def is_up_to_date(self) -> bool:
        """Check if the metadata is up to date."""
        ...


__all__ = ["ProtocolMetadata"]
