"""Transaction state enumeration for tracking transaction lifecycle."""

from enum import Enum, unique


@unique
class EnumTransactionState(Enum):
    """Transaction state tracking."""

    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
