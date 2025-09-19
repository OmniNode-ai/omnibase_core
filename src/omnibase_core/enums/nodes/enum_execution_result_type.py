"""
Execution result type enumeration.

Provides strongly typed result types for node execution operations.
"""

from enum import Enum


class EnumExecutionResultType(str, Enum):
    """Type of execution result."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
