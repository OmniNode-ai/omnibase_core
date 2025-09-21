"""
Performance metric data type definition.

TypedDict for performance metric values to replace loose Any typing.
"""

from __future__ import annotations

from typing import TypedDict


class ModelPerformanceMetricData(TypedDict, total=False):
    """Typed dictionary for performance metric values."""

    name: str
    value: float  # All metrics can be represented as float
    unit: str
    category: str


# Export for use
__all__ = ["ModelPerformanceMetricData"]
