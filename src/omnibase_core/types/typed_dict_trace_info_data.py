from __future__ import annotations

"""
TypedDict for trace information data.

Strongly-typed representation for trace information to replace loose Any typing.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""


from datetime import datetime
from typing import TypedDict


class TypedDictTraceInfoData(TypedDict, total=False):
    """Strongly-typed dict[str, Any]ionary for trace information."""

    key: str
    value: str  # Trace values are typically displayed as strings
    timestamp: datetime
    operation: str


# Export for use
__all__ = ["TypedDictTraceInfoData"]
