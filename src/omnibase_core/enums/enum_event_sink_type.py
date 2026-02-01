"""Event sink type enumeration for contract validation event destinations."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumEventSinkType"]


@unique
class EnumEventSinkType(StrValueHelper, str, Enum):
    """Event sink types for contract validation events.

    Types: MEMORY (in-memory), FILE (JSONL), KAFKA (streaming).
    """

    MEMORY = "memory"
    FILE = "file"
    KAFKA = "kafka"

    @property
    def is_persistent(self) -> bool:
        """
        Check if this sink type provides persistent storage.

        Returns:
            bool: True for FILE and KAFKA, False for MEMORY.

        Example:
            >>> EnumEventSinkType.MEMORY.is_persistent
            False
            >>> EnumEventSinkType.FILE.is_persistent
            True
        """
        return self in {EnumEventSinkType.FILE, EnumEventSinkType.KAFKA}

    @property
    def requires_path(self) -> bool:
        """
        Check if this sink type requires a file path.

        Returns:
            bool: True for FILE, False otherwise.
        """
        return self == EnumEventSinkType.FILE

    @property
    def requires_connection(self) -> bool:
        """
        Check if this sink type requires a network connection.

        Returns:
            bool: True for KAFKA, False otherwise.
        """
        return self == EnumEventSinkType.KAFKA
