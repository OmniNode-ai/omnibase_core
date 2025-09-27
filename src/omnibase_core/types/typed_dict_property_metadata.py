"""
TypedDict for property metadata structures.

This TypedDict provides type safety for property metadata dictionaries
used in environment properties collection systems.
"""

from typing_extensions import TypedDict


class TypedDictPropertyMetadata(TypedDict, total=False):
    """Metadata for environment properties."""

    description: str
    source: str
