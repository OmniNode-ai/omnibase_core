from __future__ import annotations

"""
Legacy health input structure for converter functions.
"""

from datetime import datetime
from typing import TypedDict


class TypedDictLegacyHealth(TypedDict, total=False):
    """Legacy health input structure for converter functions."""

    status: str | None
    uptime_seconds: str | None
    last_check: datetime | None
    error_count: str | None
    warning_count: str | None
    checks_passed: str | None
    checks_total: str | None


__all__ = ["TypedDictLegacyHealth"]
