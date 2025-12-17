"""
Protocol definition for validation decorator functionality.

This module provides the ProtocolValidationDecorator protocol which provides
decorator-based validation for protocol implementations.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.validation.protocol_validation_result import (
        ProtocolValidationResult,
    )


@runtime_checkable
class ProtocolValidationDecorator(Protocol):
    """
    Protocol for validation decorator functionality.

    Provides decorator-based validation for protocol implementations.
    """

    async def validate_protocol_implementation(
        self, implementation: object, protocol: type[object], strict: bool | None = None
    ) -> ProtocolValidationResult:
        """
        Validate a protocol implementation.

        Args:
            implementation: The implementation to validate
            protocol: The protocol type
            strict: Optional strict mode override

        Returns:
            Validation result
        """
        ...

    def validation_decorator(self, protocol: type[object]) -> object:
        """
        Create a validation decorator for a protocol.

        Args:
            protocol: The protocol type

        Returns:
            Decorator function
        """
        ...


__all__ = ["ProtocolValidationDecorator"]
