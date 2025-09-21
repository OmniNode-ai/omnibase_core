"""
Status Message Enum.

Strongly typed status message values for progress tracking.
"""

from __future__ import annotations

from enum import Enum


class EnumStatusMessage(str, Enum):
    """Strongly typed status message values."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Export for use
__all__ = ["EnumStatusMessage"]