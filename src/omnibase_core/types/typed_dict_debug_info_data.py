"""
TypedDict for debug information data.

Strongly-typed representation for debug information to replace loose Any typing.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictDebugInfoData(TypedDict, total=False):
    """Strongly-typed dictionary for debug information."""

    key: str
    value: str  # Debug values are typically displayed as strings
    timestamp: datetime
    category: str


# Export for use
__all__ = ["TypedDictDebugInfoData"]
