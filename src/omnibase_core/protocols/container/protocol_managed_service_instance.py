"""
Protocol for service registry managed instance information.

This module provides the ProtocolManagedServiceInstance protocol which
represents an active instance of a registered service with
lifecycle and usage tracking.

Note: This is distinct from ProtocolServiceInstance in protocols/types/
which is used for service discovery and health monitoring at the network level.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.enums import EnumInjectionScope, EnumServiceLifecycle
from omnibase_core.protocols.base import (
    ContextValue,
    ProtocolDateTime,
)


@runtime_checkable
class ProtocolManagedServiceInstance(Protocol):
    """
    Protocol for service registry managed instance information.

    Represents an active instance of a registered service within the DI container
    with lifecycle and usage tracking.

    This protocol is for DI container-level service management. For network-level
    service discovery, see ProtocolServiceInstance in protocols/types/.
    """

    instance_id: UUID
    service_registration_id: UUID
    instance: Any
    lifecycle: EnumServiceLifecycle
    scope: EnumInjectionScope
    created_at: ProtocolDateTime
    last_accessed: ProtocolDateTime
    access_count: int
    is_disposed: bool
    metadata: dict[str, ContextValue]

    async def validate_instance(self) -> bool:
        """Validate that instance is valid and ready."""
        ...

    def is_active(self) -> bool:
        """Check if instance is currently active."""
        ...


__all__ = ["ProtocolManagedServiceInstance"]
