from __future__ import annotations

from typing import Dict, TypedDict

"""
Trace info data type definition.

TypedDict for trace information to replace loose Any typing.
"""


from typing import TypedDict


class TypedDictTraceInfoData(TypedDict, total=False):
    """Typed dict[str, Any]ionary for trace information."""

    key: str
    value: str  # Trace values are typically displayed as strings
    timestamp: str
    operation: str


# Export for use
__all__ = ["TypedDictTraceInfoData"]
