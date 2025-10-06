"""
Action Category Enum

Categories for organizing different types of actions across tools.
"""

from enum import Enum


class EnumActionCategory(str, Enum):
    """
    Categories for organizing different types of actions across tools.

    Provides consistent categorization for action organization and filtering.
    """

    SYSTEM = "system"
    DATABASE = "database"
    RESOURCE = "resource"
    NETWORK = "network"
    SECURITY = "security"
    MONITORING = "monitoring"
    MAINTENANCE = "maintenance"
    CONFIGURATION = "configuration"
    DEVELOPMENT = "development"

    def __str__(self) -> str:
        """Return the string value of the category."""
        return self.value

    def is_system_level(self) -> bool:
        """Check if this category involves system-level operations."""
        return self in [self.SYSTEM, self.RESOURCE, self.SECURITY, self.CONFIGURATION]

    def is_infrastructure(self) -> bool:
        """Check if this category involves infrastructure operations."""
        return self in [self.DATABASE, self.NETWORK, self.MONITORING, self.MAINTENANCE]
