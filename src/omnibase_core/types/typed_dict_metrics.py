from __future__ import annotations

"""
TypedDict for general metrics.
"""

from datetime import datetime
from typing import TypedDict


class TypedDictMetrics(TypedDict):
    """TypedDict for general metrics."""

    timestamp: datetime
    metric_name: str
    metric_value: float
    metric_unit: str
    tags: dict[str, str]


__all__ = ["TypedDictMetrics"]
