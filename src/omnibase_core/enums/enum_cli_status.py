"""
CLI Status Enum.

Strongly typed status values for CLI operations.
"""

from __future__ import annotations

from enum import Enum


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
