"""ONEX Status Enum for import compatibility."""

from enum import Enum


class EnumOnexStatus(str, Enum):
    """ONEX status enumeration."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"
    FIXED = "fixed"
    PARTIAL = "partial"
    INFO = "info"
    UNKNOWN = "unknown"