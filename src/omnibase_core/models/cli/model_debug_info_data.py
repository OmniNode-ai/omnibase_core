"""
Debug info data type definition.

TypedDict for debug information to replace loose Any typing.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictModelDebugInfoData(TypedDict, total=False):
    """Typed dictionary for debug information."""

    key: str
    value: str  # Debug values are typically displayed as strings
    timestamp: str
    category: str


# Export for use
__all__ = ["TypedDictModelDebugInfoData"]
