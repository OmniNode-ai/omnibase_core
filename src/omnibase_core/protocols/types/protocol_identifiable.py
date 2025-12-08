"""
ProtocolIdentifiable - Protocol for identifiable objects.

This module provides the protocol definition for objects that have an ID.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolIdentifiable(Protocol):
    """
    Protocol for objects that have an ID.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_identifiable_marker__: Literal[True]

    @property
    def id(self) -> UUID:
        """Get the object's unique identifier."""
        ...


__all__ = ["ProtocolIdentifiable"]
