"""
Protocol for service registry managed instance information.

This module provides the ProtocolServiceInstance protocol which
represents an active instance of a registered service with
lifecycle and usage tracking.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from omnibase_core.protocols.base import (
    ContextValue,
    LiteralInjectionScope,
    LiteralServiceLifecycle,
    ProtocolDateTime,
)


@runtime_checkable
class ProtocolServiceInstance(Protocol):
    """
    Protocol for service registry managed instance information.

    Represents an active instance of a registered service with
    lifecycle and usage tracking.
    """

    instance_id: str
    service_registration_id: str
    instance: Any
    lifecycle: LiteralServiceLifecycle
    scope: LiteralInjectionScope
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


__all__ = ["ProtocolServiceInstance"]
