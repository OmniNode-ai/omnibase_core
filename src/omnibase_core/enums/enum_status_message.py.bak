from __future__ import annotations

"""
Status Message Enum.

Strongly typed status message values for progress tracking.
"""


from enum import Enum, unique


@unique
class EnumStatusMessage(str, Enum):
    """Strongly typed status message values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Export for use
__all__ = ["EnumStatusMessage"]
