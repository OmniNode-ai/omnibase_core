"""
TypedDict for execution statistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictExecutionStats(TypedDict):
    execution_count: int
    success_count: int
    failure_count: int
    average_duration_ms: float
    last_execution: datetime
    total_duration_ms: int


__all__ = ["TypedDictExecutionStats"]
