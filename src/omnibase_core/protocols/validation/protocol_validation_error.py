"""
Protocol definition for validation error objects.

This module provides the ProtocolValidationError protocol which represents
a single validation error with type, message, context, and severity information.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolValidationError(Protocol):
    """
    Protocol for validation error objects.

    Represents a single validation error with type, message, context,
    and severity information.
    """

    error_type: str
    message: str
    context: dict[str, ContextValue]
    severity: str

    def __str__(self) -> str:
        """Return string representation of the error."""
        ...


__all__ = ["ProtocolValidationError"]
