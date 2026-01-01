"""
Protocol for service factory operations.

This module provides the ProtocolServiceFactory protocol which
defines the interface for service instance creation with dependency
injection support and lifecycle management.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- NO Any types - use object for maximum flexibility where needed
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from omnibase_core.protocols.base import ContextValue

T = TypeVar("T")


@runtime_checkable
class ProtocolServiceFactory(Protocol):
    """
    Protocol for service factory operations.

    Defines the interface for service instance creation with dependency
    injection support and lifecycle management.

    The factory is responsible for:
    - Creating new service instances with proper dependency injection
    - Managing the lifecycle of created instances
    - Disposing of instances when no longer needed

    Example:
        class MyServiceFactory:
            async def create_instance(
                self, interface: type[T], context: dict[str, ContextValue]
            ) -> T:
                # Create and return instance
                return instance

            async def dispose_instance(self, instance: object) -> None:
                # Clean up instance resources
                pass
    """

    async def create_instance(
        self, interface: type[T], context: dict[str, ContextValue]
    ) -> T:
        """
        Create a new service instance with dependency injection.

        Args:
            interface: The interface type to create an instance for
            context: Injection context with configuration values

        Returns:
            A new instance implementing the specified interface
        """
        ...

    async def dispose_instance(self, instance: object) -> None:
        """
        Dispose of a service instance.

        Cleans up any resources held by the instance and removes it
        from the container's management.

        Args:
            instance: The service instance to dispose
        """
        ...


__all__ = ["ProtocolServiceFactory"]
