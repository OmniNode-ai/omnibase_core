"""
Daemon Action Type Enum

Action types for daemon management operations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDaemonActionType(StrValueHelper, str, Enum):
    """
    Action types for daemon management operations.

    Defines the categories of operations that can be performed on the daemon.
    """

    LIFECYCLE = "lifecycle"
    HEALTH = "health"
    STATUS = "status"
    CONFIGURATION = "configuration"
    SERVICE_MANAGEMENT = "service_management"
    MONITORING = "monitoring"

    def is_destructive(self) -> bool:
        """Check if this action type typically involves destructive operations."""
        return self in {self.LIFECYCLE, self.SERVICE_MANAGEMENT, self.CONFIGURATION}

    def requires_confirmation(self) -> bool:
        """Check if this action type typically requires user confirmation."""
        return self in {self.LIFECYCLE, self.SERVICE_MANAGEMENT}
