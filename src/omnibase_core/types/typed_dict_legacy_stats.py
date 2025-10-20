from __future__ import annotations

"""
Legacy stats input structure for converter functions.
"""


from datetime import datetime
from typing import Dict, TypedDict


class TypedDictLegacyStats(TypedDict, total=False):
    """Legacy stats input structure for converter functions."""

    execution_count: str | None
    success_count: str | None
    failure_count: str | None
    average_duration_ms: str | None
    last_execution: datetime | None
    total_duration_ms: str | None
