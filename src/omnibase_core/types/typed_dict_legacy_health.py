"""
Legacy health input structure for converter functions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictLegacyHealth(TypedDict, total=False):
    status: str | None
    uptime_seconds: str | None
    last_check: datetime | None
    error_level_count: str | None
    warning_count: str | None
    checks_passed: str | None
    checks_total: str | None


__all__ = ["TypedDictLegacyHealth"]
