"""
ONEX Reply Enums.

Standard ONEX reply status values.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOnexReplyStatus(StrValueHelper, str, Enum):
    """Standard ONEX reply status values."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"


__all__ = ["EnumOnexReplyStatus"]
