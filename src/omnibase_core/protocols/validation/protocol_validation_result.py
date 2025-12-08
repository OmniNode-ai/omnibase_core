"""
Protocol definition for validation result objects.

This module provides the ProtocolValidationResult protocol which contains
the overall validation status, errors, and warnings.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue

if TYPE_CHECKING:
    from omnibase_core.protocols.validation.protocol_validation_error import (
        ProtocolValidationError,
    )


@runtime_checkable
class ProtocolValidationResult(Protocol):
    """
    Protocol for validation result objects.

    Contains the overall validation status, errors, and warnings.
    """

    is_valid: bool
    protocol_name: str
    implementation_name: str
    errors: list[ProtocolValidationError]
    warnings: list[ProtocolValidationError]

    def add_error(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
        severity: str | None = None,
    ) -> None:
        """
        Add an error to the result.

        Args:
            error_type: Type of the error
            message: Error message
            context: Optional context data
            severity: Optional severity level
        """
        ...

    def add_warning(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
    ) -> None:
        """
        Add a warning to the result.

        Args:
            error_type: Type of the warning
            message: Warning message
            context: Optional context data
        """
        ...

    async def get_summary(self) -> str:
        """
        Get a summary of the validation result.

        Returns:
            Summary string
        """
        ...


__all__ = ["ProtocolValidationResult"]
