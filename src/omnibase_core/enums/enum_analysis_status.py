"""
Analysis status enumeration for document analysis operations.

ONEX-compatible enum for standardized analysis status values.
"""

from enum import Enum


class EnumAnalysisStatus(str, Enum):
    """Enumeration for analysis status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
