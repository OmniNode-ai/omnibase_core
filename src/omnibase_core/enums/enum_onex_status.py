"""
ONEX Status Enumeration

Standardized status codes for ONEX operations.
"""

from enum import Enum, unique


@unique
class EnumOnexStatus(str, Enum):
    """Status codes for ONEX operations."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"
    FIXED = "fixed"
    PARTIAL = "partial"
    INFO = "info"
    UNKNOWN = "unknown"


__all__ = ["EnumOnexStatus"]
