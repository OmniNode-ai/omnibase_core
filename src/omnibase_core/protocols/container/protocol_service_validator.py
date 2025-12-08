"""
Protocol for service validation operations.

This module provides the ProtocolServiceValidator protocol which
defines the interface for comprehensive service validation including
interface compliance checking and dependency validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.container.protocol_service_dependency import (
        ProtocolServiceDependency,
    )
    from omnibase_core.protocols.container.protocol_validation_result import (
        ProtocolValidationResult,
    )


@runtime_checkable
class ProtocolServiceValidator(Protocol):
    """
    Protocol for service validation operations.

    Defines the interface for comprehensive service validation including
    interface compliance checking and dependency validation.
    """

    async def validate_service(
        self, service: Any, interface: type[Any]
    ) -> ProtocolValidationResult:
        """Validate that a service implementation conforms to its interface."""
        ...

    async def validate_dependencies(
        self, dependencies: list[ProtocolServiceDependency]
    ) -> ProtocolValidationResult:
        """Validate that all dependencies can be satisfied."""
        ...


__all__ = ["ProtocolServiceValidator"]
