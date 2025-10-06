from __future__ import annotations

from typing import Dict, TypedDict

"""
Performance metric data type definition.

TypedDict for performance metric values to replace loose Any typing.
"""


from typing import TypedDict


class TypedDictPerformanceMetricData(TypedDict, total=False):
    """Typed dict[str, Any]ionary for performance metric values."""

    name: str
    value: float  # All metrics can be represented as float
    unit: str
    category: str


# Export for use
__all__ = ["TypedDictPerformanceMetricData"]
