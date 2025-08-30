"""Sync Status enumeration generated from contract."""

from enum import Enum


class EnumSyncStatus(Enum):
    """Status of file synchronization operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
