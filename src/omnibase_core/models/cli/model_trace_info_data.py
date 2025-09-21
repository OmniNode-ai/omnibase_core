"""
Trace info data type definition.

TypedDict for trace information to replace loose Any typing.
"""

from __future__ import annotations

from typing import TypedDict


class ModelTraceInfoData(TypedDict, total=False):
    """Typed dictionary for trace information."""

    key: str
    value: str  # Trace values are typically displayed as strings
    timestamp: str
    operation: str


# Export for use
__all__ = ["ModelTraceInfoData"]
