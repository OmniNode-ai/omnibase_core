"""
TypedDict for performance metric data.

Strongly-typed representation for performance metric values to replace loose Any typing.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictPerformanceMetricData(TypedDict, total=False):
    """Strongly-typed dictionary for performance metric values."""

    name: str
    value: float  # All metrics can be represented as float
    unit: str
    category: str


# Export for use
__all__ = ["TypedDictPerformanceMetricData"]
