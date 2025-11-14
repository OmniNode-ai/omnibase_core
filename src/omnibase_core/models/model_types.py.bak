"""
Type definitions for models.

Provides common type aliases used across model definitions.
"""

from typing import TypeAlias

# JSON-serializable types that match JSON specification
# This recursive type represents all values that can be serialized to JSON
type JsonSerializable = (
    str
    | int
    | float
    | bool
    | None
    | dict[str, "JsonSerializable"]
    | list["JsonSerializable"]
)

__all__ = []
