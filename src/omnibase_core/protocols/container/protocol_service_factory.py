"""
Protocol for service factory operations.

This module provides the ProtocolServiceFactory protocol which
defines the interface for service instance creation with dependency
injection support and lifecycle management.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from omnibase_core.protocols.base import ContextValue

T = TypeVar("T")


@runtime_checkable
class ProtocolServiceFactory(Protocol):
    """
    Protocol for service factory operations.

    Defines the interface for service instance creation with dependency
    injection support and lifecycle management.
    """

    async def create_instance(
        self, interface: type[T], context: dict[str, ContextValue]
    ) -> T:
        """Create a new service instance with dependency injection."""
        ...

    async def dispose_instance(self, instance: Any) -> None:
        """Dispose of a service instance."""
        ...


__all__ = ["ProtocolServiceFactory"]
