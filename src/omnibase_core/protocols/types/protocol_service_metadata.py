"""
ProtocolServiceMetadata - Protocol for service metadata.

This module provides the protocol definition for service metadata including
capabilities and tags.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue, ProtocolSemVer


@runtime_checkable
class ProtocolServiceMetadata(Protocol):
    """
    Protocol for service metadata.

    Contains metadata about a service including capabilities and tags.
    """

    data: dict[str, ContextValue]
    version: ProtocolSemVer
    capabilities: list[str]
    tags: list[str]

    async def validate_service_metadata(self) -> bool:
        """Validate the service metadata."""
        ...

    def has_capabilities(self) -> bool:
        """Check if the service has capabilities."""
        ...


__all__ = ["ProtocolServiceMetadata"]
