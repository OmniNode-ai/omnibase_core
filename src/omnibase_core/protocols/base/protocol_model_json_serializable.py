"""
ModelJsonSerializable Protocol.

Marker protocol for objects that can be safely serialized to JSON.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class ProtocolModelJsonSerializable(Protocol):
    """
    Protocol for values that can be JSON serialized.

    Marker protocol for objects that can be safely serialized to JSON.
    """

    __omnibase_json_serializable_marker__: Literal[True]


__all__ = ["ProtocolModelJsonSerializable"]
