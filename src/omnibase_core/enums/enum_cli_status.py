"""
CLI Status Enum.

Strongly typed status values for CLI operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliStatus(StrValueHelper, str, Enum):
    """Strongly typed status values for CLI operations."""

    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    RUNNING = "running"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# Export for use
__all__ = ["EnumCliStatus"]
