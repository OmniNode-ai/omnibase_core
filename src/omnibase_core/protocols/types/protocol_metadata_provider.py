"""
ProtocolMetadataProvider - Protocol for metadata providers.

This module provides the protocol definition for objects that provide metadata.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class ProtocolMetadataProvider(Protocol):
    """
    Protocol for objects that provide metadata.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_metadata_provider_marker__: Literal[True]

    # union-ok: json_value - standard JSON-compatible metadata types
    async def get_metadata(self) -> dict[str, str | int | bool | float]:
        """Get the object's metadata."""
        ...


__all__ = ["ProtocolMetadataProvider"]
