"""
TypedDict for version dictionary.

Strongly-typed representation for version dictionary structure.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictVersionDict(TypedDict):
    """Strongly-typed version dictionary structure."""

    major: int
    minor: int
    patch: int


__all__ = ["TypedDictVersionDict"]
