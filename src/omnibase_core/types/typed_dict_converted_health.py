"""TypedDict for converted legacy health data.

Represents the output of converting TypedDictLegacyHealth to a typed structure.
This is separate from TypedDictHealthStatus which is used by MixinHealthCheck.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictConvertedHealth(TypedDict):
    """TypedDict for converted legacy health data.

    Used by convert_health_to_typed_dict() to provide precise typing
    for converted legacy health dictionaries.

    Attributes:
        status: Health status string
        uptime_seconds: Uptime in seconds
        last_check: Last check datetime or None
        error_level_count: Number of errors at ERROR severity level
        warning_count: Number of warnings at WARNING severity level
        checks_passed: Number of checks passed
        checks_total: Total number of checks
    """

    status: str
    uptime_seconds: int
    last_check: datetime | None
    error_level_count: int
    warning_count: int
    checks_passed: int
    checks_total: int


__all__ = ["TypedDictConvertedHealth"]
