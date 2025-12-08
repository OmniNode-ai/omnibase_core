"""
ProtocolSerializable - Protocol for serializable objects.

This module provides the protocol definition for objects that can be
serialized to dictionary format.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSerializable(Protocol):
    """
    Protocol for objects that can be serialized to dictionary format.

    Provides standardized serialization contract for ONEX objects that need
    to be persisted, transmitted, or cached.
    """

    # union-ok: json_value - serialization output uses standard JSON-compatible types
    def model_dump(
        self,
    ) -> dict[
        str,
        str
        | int
        | float
        | bool
        | list[str | int | float | bool]
        | dict[str, str | int | float | bool],
    ]:
        """Serialize the object to a dictionary."""
        ...


__all__ = ["ProtocolSerializable"]
