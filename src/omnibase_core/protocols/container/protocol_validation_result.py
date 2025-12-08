"""
Protocol for validation result objects.

This module provides the ProtocolValidationResult protocol which
is a forward declaration to avoid circular imports with the validation module.
See validation.py for the complete definition.
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

    Forward declaration to avoid circular imports with validation module.
    See validation.py for the complete definition.
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
        """Add an error to the result."""
        ...

    def add_warning(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
    ) -> None:
        """Add a warning to the result."""
        ...

    async def get_summary(self) -> str:
        """Get result summary."""
        ...


__all__ = ["ProtocolValidationResult"]
