"""
ProtocolValidatable - Protocol for validatable objects.

This module provides the protocol definition for objects that can be validated.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolValidatable(Protocol):
    """
    Protocol for objects that can be validated.

    Defines the minimal interface that validation targets should implement
    to provide context and metadata for validation operations.
    """

    async def get_validation_context(self) -> dict[str, ContextValue]:
        """Get context for validation rules."""
        ...

    async def get_validation_id(self) -> UUID:
        """Get unique identifier for validation reporting."""
        ...


__all__ = ["ProtocolValidatable"]
