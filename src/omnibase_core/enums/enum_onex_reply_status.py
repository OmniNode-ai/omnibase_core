"""
ONEX Reply Enums.

Standard ONEX reply status values.
"""

from enum import Enum


class EnumOnexReplyStatus(str, Enum):
    """Standard ONEX reply status values."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"
