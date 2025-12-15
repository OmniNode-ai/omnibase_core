from __future__ import annotations

"""
Convert legacy health dict[str, Any] to TypedDict.
"""


from .typed_dict_converted_health import TypedDictConvertedHealth
from .typed_dict_legacy_health import TypedDictLegacyHealth
from .util_datetime_parser import parse_datetime


def convert_health_to_typed_dict(
    health: TypedDictLegacyHealth,
) -> TypedDictConvertedHealth:
    """Convert legacy health dict[str, Any] to TypedDict."""
    return TypedDictConvertedHealth(
        status=str(health.get("status", "unknown")),
        uptime_seconds=int(health.get("uptime_seconds", 0) or 0),
        last_check=parse_datetime(health.get("last_check")),
        error_count=int(health.get("error_count", 0) or 0),
        warning_count=int(health.get("warning_count", 0) or 0),
        checks_passed=int(health.get("checks_passed", 0) or 0),
        checks_total=int(health.get("checks_total", 0) or 0),
    )
