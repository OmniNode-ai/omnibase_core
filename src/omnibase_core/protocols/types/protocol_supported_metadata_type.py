"""
ProtocolSupportedMetadataType - Protocol for metadata types.

This module provides the protocol definition for types that can be stored
in ONEX metadata systems.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class ProtocolSupportedMetadataType(Protocol):
    """
    Protocol for types that can be stored in ONEX metadata systems.

    This marker protocol defines the contract for objects that can be safely
    stored, serialized, and retrieved from metadata storage systems.
    """

    __omnibase_metadata_type_marker__: Literal[True]

    def __str__(self) -> str:
        """Convert to string for storage."""
        ...

    async def validate_for_metadata(self) -> bool:
        """Validate the value for metadata storage."""
        ...


__all__ = ["ProtocolSupportedMetadataType"]
