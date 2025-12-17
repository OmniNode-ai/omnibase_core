"""
Protocol definition for protocol validation functionality.

This module provides the ProtocolValidator protocol which validates that
implementations conform to their protocol interfaces.

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
class ProtocolValidator(Protocol):
    """
    Protocol for protocol validation functionality.

    Validates that implementations conform to their protocol interfaces.
    """

    strict_mode: bool

    async def validate_implementation(
        self, implementation: object, protocol: type[object]
    ) -> ProtocolValidationResult:
        """
        Validate that an implementation conforms to a protocol.

        Args:
            implementation: The implementation to validate
            protocol: The protocol type to validate against

        Returns:
            Validation result
        """
        ...


__all__ = ["ProtocolValidator"]
