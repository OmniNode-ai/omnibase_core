"""
ProtocolServiceInstance - Protocol for service instances.

This module provides the protocol definition for service instance information
used for service discovery and health monitoring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import ProtocolDateTime

if TYPE_CHECKING:
    from omnibase_core.protocols.types.protocol_service_metadata import (
        ProtocolServiceMetadata,
    )


@runtime_checkable
class ProtocolServiceInstance(Protocol):
    """
    Protocol for service instance information.

    Used for service discovery and health monitoring.
    """

    service_id: UUID
    service_name: str
    host: str
    port: int
    metadata: ProtocolServiceMetadata
    health_status: str
    last_seen: ProtocolDateTime

    async def validate_service_instance(self) -> bool:
        """Validate the service instance."""
        ...

    def is_available(self) -> bool:
        """Check if the service is available."""
        ...


__all__ = ["ProtocolServiceInstance"]
