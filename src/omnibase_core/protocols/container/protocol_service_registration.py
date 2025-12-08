"""
Protocol for service registration information.

This module provides the ProtocolServiceRegistration protocol which
defines the interface for comprehensive service registration metadata
including lifecycle management, dependency tracking, and health monitoring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import (
    LiteralHealthStatus,
    LiteralInjectionScope,
    LiteralServiceLifecycle,
    ProtocolDateTime,
)

if TYPE_CHECKING:
    from omnibase_core.protocols.container.protocol_service_dependency import (
        ProtocolServiceDependency,
    )
    from omnibase_core.protocols.container.protocol_service_registration_metadata import (
        ProtocolServiceRegistrationMetadata,
    )


@runtime_checkable
class ProtocolServiceRegistration(Protocol):
    """
    Protocol for service registration information.

    Defines the interface for comprehensive service registration metadata
    including lifecycle management, dependency tracking, and health monitoring.
    """

    registration_id: UUID
    service_metadata: ProtocolServiceRegistrationMetadata
    lifecycle: LiteralServiceLifecycle
    scope: LiteralInjectionScope
    dependencies: list[ProtocolServiceDependency]
    registration_status: Literal[
        "registered", "unregistered", "failed", "pending", "conflict", "invalid"
    ]
    health_status: LiteralHealthStatus
    registration_time: ProtocolDateTime
    last_access_time: ProtocolDateTime | None
    access_count: int
    instance_count: int
    max_instances: int | None

    async def validate_registration(self) -> bool:
        """Validate that registration is valid and complete."""
        ...

    def is_active(self) -> bool:
        """Check if this registration is currently active."""
        ...


__all__ = ["ProtocolServiceRegistration"]
