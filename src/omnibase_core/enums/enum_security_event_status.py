"""
Security Event Status Enumeration.

Strongly typed enumeration for security event statuses.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSecurityEventStatus(StrValueHelper, str, Enum):
    """Enumeration for security event statuses."""

    # Success statuses
    SUCCESS = "success"
    COMPLETED = "completed"

    # Failure statuses
    FAILED = "failed"
    DENIED = "denied"
    ERROR = "error"

    # In-progress statuses
    PENDING = "pending"
    IN_PROGRESS = "in_progress"

    # Other statuses
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


__all__ = ["EnumSecurityEventStatus"]
