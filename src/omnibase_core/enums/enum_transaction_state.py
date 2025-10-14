"""Transaction state enumeration for tracking transaction lifecycle."""

from enum import Enum


class EnumTransactionState(Enum):
    """Transaction state tracking."""

    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
