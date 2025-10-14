"""
TypedDict for input state source.

Strongly-typed representation for input state source structure.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictInputStateSourceType(TypedDict, total=False):
    """Strongly-typed input state source structure."""

    version: object | None  # Use object with runtime type checking instead of Any
    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str


__all__ = ["TypedDictInputStateSourceType"]
