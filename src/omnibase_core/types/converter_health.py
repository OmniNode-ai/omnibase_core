"""
Convert legacy health dict[str, Any] to TypedDict.
"""

from __future__ import annotations

from .typed_dict_converted_health import TypedDictConvertedHealth
from .typed_dict_legacy_health import TypedDictLegacyHealth


def convert_health_to_typed_dict(
    health: TypedDictLegacyHealth,
) -> TypedDictConvertedHealth:
    """Convert legacy health dict[str, Any] to TypedDict."""
    # Lazy import to avoid circular import:
    # types -> utils -> models.errors -> types
    from omnibase_core.utils.util_datetime_parser import parse_datetime

    return TypedDictConvertedHealth(
        status=str(health.get("status", "unknown")),
        uptime_seconds=int(health.get("uptime_seconds", 0) or 0),
        last_check=parse_datetime(health.get("last_check")),
        error_level_count=int(health.get("error_level_count", 0) or 0),
        warning_count=int(health.get("warning_count", 0) or 0),
        checks_passed=int(health.get("checks_passed", 0) or 0),
        checks_total=int(health.get("checks_total", 0) or 0),
    )
