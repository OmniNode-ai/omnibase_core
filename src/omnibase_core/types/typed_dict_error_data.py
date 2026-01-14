"""
TypedDict for error count statistics.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictErrorData(TypedDict, total=False):
    """Typed structure for error count statistics in metadata analytics."""

    error_level_count: int
    warning_count: int
    critical_error_count: int


__all__ = ["TypedDictErrorData"]
