"""Severity levels for violations and issues."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSeverity(StrValueHelper, str, Enum):
    """Severity levels for violations."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


__all__ = ["EnumSeverity"]
