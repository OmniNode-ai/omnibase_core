"""
TypedDict for general metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictMetrics(TypedDict):
    timestamp: datetime
    metric_name: str
    metric_value: float
    metric_unit: str
    tags: dict[str, str]


__all__ = ["TypedDictMetrics"]
