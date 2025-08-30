"""
Security Event Status Enumeration.

Strongly typed enumeration for security event statuses.
"""

from enum import Enum


class EnumSecurityEventStatus(str, Enum):
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
