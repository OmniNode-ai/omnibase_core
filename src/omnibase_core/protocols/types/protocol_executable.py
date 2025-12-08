"""
ProtocolExecutable - Protocol for executable objects.

This module provides the protocol definition for objects that can be executed.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class ProtocolExecutable(Protocol):
    """
    Protocol for objects that can be executed.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_executable_marker__: Literal[True]

    async def execute(self) -> object:
        """Execute the object and return a result."""
        ...


__all__ = ["ProtocolExecutable"]
