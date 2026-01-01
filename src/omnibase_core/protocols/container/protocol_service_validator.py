"""
Protocol for service validation operations.

This module provides the ProtocolServiceValidator protocol which
defines the interface for comprehensive service validation including
interface compliance checking and dependency validation.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- NO Any types - use object for maximum flexibility where needed
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

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

    The validator is responsible for:
    - Checking that service implementations conform to their interfaces
    - Validating that all declared dependencies can be satisfied
    - Producing detailed validation results with error information

    Example:
        class MyServiceValidator:
            async def validate_service(
                self, service: object, interface: type[object]
            ) -> ProtocolValidationResult:
                # Check service conforms to interface
                return validation_result

            async def validate_dependencies(
                self, dependencies: list[ProtocolServiceDependency]
            ) -> ProtocolValidationResult:
                # Check all dependencies can be resolved
                return validation_result
    """

    async def validate_service(
        self, service: object, interface: type[object]
    ) -> ProtocolValidationResult:
        """
        Validate that a service implementation conforms to its interface.

        Args:
            service: The service instance to validate
            interface: The interface type the service should conform to

        Returns:
            Validation result indicating success or failure with details
        """
        ...

    async def validate_dependencies(
        self, dependencies: list[ProtocolServiceDependency]
    ) -> ProtocolValidationResult:
        """
        Validate that all dependencies can be satisfied.

        Args:
            dependencies: List of service dependencies to validate

        Returns:
            Validation result indicating if all dependencies can be resolved
        """
        ...


__all__ = ["ProtocolServiceValidator"]
