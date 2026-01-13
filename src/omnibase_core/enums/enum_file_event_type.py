"""File Event Type enumeration generated from contract."""

from enum import Enum, unique


@unique
class EnumFileEventType(Enum):
    """Types of filesystem events that can be monitored."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    RENAMED = "renamed"
    PERMISSION_CHANGED = "permission_changed"
    ATTRIBUTE_CHANGED = "attribute_changed"
