"""
TypedDict for JSON Schema reference component parts.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictRefParts(TypedDict):
    """TypedDict for reference component parts.

    Used for parsing JSON Schema $ref references into their constituent parts
    for code generation and schema resolution.

    Attributes:
        file: The file path component of the reference, or None for internal refs
        path: The JSON path component within the schema
        name: The definition/type name extracted from the reference
    """

    file: str | None
    path: str | None
    name: str | None


__all__ = ["TypedDictRefParts"]
