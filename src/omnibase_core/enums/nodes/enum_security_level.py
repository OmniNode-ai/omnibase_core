"""
Security Level Enum for Node Operations.

Provides strongly typed security level classifications for node actions
and operations within the ONEX architecture.
"""

from enum import Enum


class EnumSecurityLevel(str, Enum):
    """
    Security level classifications for node actions and operations.

    Provides comprehensive security level options from public access
    to classified operations with clear escalation hierarchy.
    """

    # Public access - no restrictions
    PUBLIC = "public"

    # Standard access - basic authentication required
    STANDARD = "standard"

    # Elevated access - enhanced permissions required
    ELEVATED = "elevated"

    # Restricted access - special authorization required
    RESTRICTED = "restricted"

    # Classified access - highest security clearance required
    CLASSIFIED = "classified"

    @classmethod
    def get_all_levels(cls) -> list[str]:
        """Get all available security levels."""
        return [level.value for level in cls]

    @classmethod
    def get_elevated_levels(cls) -> list[str]:
        """Get security levels that require elevated permissions."""
        return [cls.ELEVATED.value, cls.RESTRICTED.value, cls.CLASSIFIED.value]

    @classmethod
    def is_elevated(cls, level: str) -> bool:
        """Check if a security level requires elevated permissions."""
        return level in cls.get_elevated_levels()

    @classmethod
    def get_hierarchy_level(cls, level: str) -> int:
        """Get numeric hierarchy level (0=lowest, 4=highest)."""
        hierarchy = {
            cls.PUBLIC.value: 0,
            cls.STANDARD.value: 1,
            cls.ELEVATED.value: 2,
            cls.RESTRICTED.value: 3,
            cls.CLASSIFIED.value: 4,
        }
        return hierarchy.get(level, 1)  # Default to standard

    @classmethod
    def can_access(cls, required_level: str, user_level: str) -> bool:
        """Check if user security level can access required level."""
        return cls.get_hierarchy_level(user_level) >= cls.get_hierarchy_level(
            required_level
        )

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"EnumSecurityLevel.{self.name}"
