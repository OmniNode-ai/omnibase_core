"""
ProtocolRegistryNode - Protocol for bootstrap registry node.

This module provides the protocol definition for registry nodes
used in bootstrap service discovery.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class ProtocolRegistryNode(Protocol):
    """
    Protocol for registry nodes in bootstrap service discovery.

    Provides service and protocol resolution for bootstrap scenarios.
    """

    def get_service(self, protocol_type: type[T]) -> T | None:
        """
        Get a service implementation for the given protocol type.

        Args:
            protocol_type: The protocol interface to resolve

        Returns:
            Service implementation or None if not found
        """
        ...

    def get_protocol(self, name: str) -> object | None:
        """
        Get a protocol implementation by name.

        Args:
            name: The protocol name to resolve

        Returns:
            Protocol implementation or None if not found
        """
        ...

    def list_services(self) -> list[str]:
        """
        List available services.

        Returns:
            List of available service names
        """
        ...


__all__ = ["ProtocolRegistryNode"]
