"""
Health Detail Type Enum.

Canonical enum for health detail types used in component health monitoring.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHealthDetailType(StrValueHelper, str, Enum):
    """Canonical health detail types for component monitoring."""

    INFO = "info"
    METRIC = "metric"
    WARNING = "warning"
    ERROR = "error"
    DIAGNOSTIC = "diagnostic"


__all__ = ["EnumHealthDetailType"]
