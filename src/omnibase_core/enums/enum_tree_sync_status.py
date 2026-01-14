"""
Tree Sync Status Enum.

Strongly typed enumeration for OnexTree synchronization status values.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTreeSyncStatus(StrValueHelper, str, Enum):
    """
    OnexTree synchronization status classifications.

    Used for tracking the synchronization state between filesystem and database.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    OK = "ok"
    DRIFT = "drift"
    ERROR = "error"
    SYNCING = "syncing"
    UNKNOWN = "unknown"

    @classmethod
    def is_synchronized(cls, status: "EnumTreeSyncStatus") -> bool:
        """Check if the tree is synchronized."""
        return status == cls.OK

    @classmethod
    def requires_sync(cls, status: "EnumTreeSyncStatus") -> bool:
        """Check if the tree requires synchronization."""
        return status in {cls.DRIFT, cls.ERROR}


# Export for use
__all__ = ["EnumTreeSyncStatus"]
