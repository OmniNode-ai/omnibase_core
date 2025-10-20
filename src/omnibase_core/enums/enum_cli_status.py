from __future__ import annotations

"""
CLI Status Enum.

Strongly typed status values for CLI operations.
"""


from enum import Enum, unique


@unique
class EnumCliStatus(str, Enum):
    """Strongly typed status values for CLI operations."""

    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    RUNNING = "running"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# Export for use
__all__ = ["EnumCliStatus"]
