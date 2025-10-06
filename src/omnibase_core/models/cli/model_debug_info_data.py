from __future__ import annotations

from typing import Dict, TypedDict

"""
Debug info data type definition.

TypedDict for debug information to replace loose Any typing.
"""


from typing import TypedDict


class TypedDictDebugInfoData(TypedDict, total=False):
    """Typed dict[str, Any]ionary for debug information."""

    key: str
    value: str  # Debug values are typically displayed as strings
    timestamp: str
    category: str


# Export for use
__all__ = ["TypedDictDebugInfoData"]
