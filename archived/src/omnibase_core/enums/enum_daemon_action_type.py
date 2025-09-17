"""
Daemon Action Type Enum

Action types for daemon management operations.
"""

from enum import Enum


class EnumDaemonActionType(str, Enum):
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

    def __str__(self) -> str:
        """Return the string value of the action type."""
        return self.value

    def is_destructive(self) -> bool:
        """Check if this action type typically involves destructive operations."""
        return self in [self.LIFECYCLE, self.SERVICE_MANAGEMENT, self.CONFIGURATION]

    def requires_confirmation(self) -> bool:
        """Check if this action type typically requires user confirmation."""
        return self in [self.LIFECYCLE, self.SERVICE_MANAGEMENT]
