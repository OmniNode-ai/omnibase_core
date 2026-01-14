"""
Category enumeration for general categorization.

Provides standardized category values for classification across the system.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCategory(StrValueHelper, str, Enum):
    """
    General category enumeration for data classification.

    Provides standardized category values that can be used across different
    models for consistent categorization and filtering.
    """

    # Primary categories
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"

    # Functional categories
    CORE = "core"
    AUXILIARY = "auxiliary"
    OPTIONAL = "optional"

    # Priority categories
    HIGH_PRIORITY = "high_priority"
    MEDIUM_PRIORITY = "medium_priority"
    LOW_PRIORITY = "low_priority"

    # System categories
    SYSTEM = "system"
    USER = "user"
    ADMIN = "admin"

    # Data categories
    METADATA = "metadata"
    CONTENT = "content"
    CONFIGURATION = "configuration"

    # Status categories
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

    # General categories
    GENERAL = "general"
    SPECIFIC = "specific"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

    def is_priority_category(self) -> bool:
        """Check if this is a priority-based category."""
        return self in {
            EnumCategory.HIGH_PRIORITY,
            EnumCategory.MEDIUM_PRIORITY,
            EnumCategory.LOW_PRIORITY,
        }

    def is_system_category(self) -> bool:
        """Check if this is a system-level category."""
        return self in {
            EnumCategory.SYSTEM,
            EnumCategory.ADMIN,
            EnumCategory.CORE,
        }

    def is_data_category(self) -> bool:
        """Check if this is a data-related category."""
        return self in {
            EnumCategory.METADATA,
            EnumCategory.CONTENT,
            EnumCategory.CONFIGURATION,
        }


# Export for use
__all__ = ["EnumCategory"]
