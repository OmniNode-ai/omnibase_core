"""
Legacy stats input structure for converter functions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictLegacyStats(TypedDict, total=False):
    execution_count: str | None
    success_count: str | None
    failure_count: str | None
    average_duration_ms: str | None
    last_execution: datetime | None
    total_duration_ms: str | None


__all__ = ["TypedDictLegacyStats"]
