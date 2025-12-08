"""
ProtocolNameable - Protocol for nameable objects.

This module provides the protocol definition for objects that have a name.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class ProtocolNameable(Protocol):
    """
    Protocol for objects that have a name.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_nameable_marker__: Literal[True]

    @property
    def name(self) -> str:
        """Get the object's name."""
        ...


__all__ = ["ProtocolNameable"]
