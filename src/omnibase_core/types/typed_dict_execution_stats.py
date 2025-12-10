from __future__ import annotations

"""
TypedDict for execution statistics.
"""

from datetime import datetime
from typing import TypedDict


class TypedDictExecutionStats(TypedDict):
    """TypedDict for execution statistics."""

    execution_count: int
    success_count: int
    failure_count: int
    average_duration_ms: float
    last_execution: datetime
    total_duration_ms: int


__all__ = ["TypedDictExecutionStats"]
