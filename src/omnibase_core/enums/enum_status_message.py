"""
Status Message Enum.

Strongly typed status message values for progress tracking.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStatusMessage(StrValueHelper, str, Enum):
    """Strongly typed status message values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Export for use
__all__ = ["EnumStatusMessage"]
