"""
Result category enumeration for CLI operations.

Defines the different categories of CLI result data.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumResultCategory(StrValueHelper, str, Enum):
    """
    Strongly typed result category for CLI operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SUCCESS = "success"  # Successful operation result
    ERROR = "error"  # Error operation result
    WARNING = "warning"  # Warning operation result
    INFO = "info"  # Informational result
    DEBUG = "debug"  # Debug information result
    PERFORMANCE = "performance"  # Performance measurement result
    SECURITY = "security"  # Security-related result
    VALIDATION = "validation"  # Validation result
    CONFIGURATION = "configuration"  # Configuration-related result
    AUDIT = "audit"  # Audit trail result

    @classmethod
    def is_error_level(cls, category: EnumResultCategory) -> bool:
        """Check if the category represents an error level."""
        return category in {cls.ERROR, cls.WARNING}

    @classmethod
    def is_informational_level(cls, category: EnumResultCategory) -> bool:
        """Check if the category is informational."""
        return category in {cls.SUCCESS, cls.INFO, cls.DEBUG}

    @classmethod
    def is_operational_category(cls, category: EnumResultCategory) -> bool:
        """Check if the category is operational."""
        return category in {
            cls.SUCCESS,
            cls.ERROR,
            cls.WARNING,
            cls.CONFIGURATION,
        }

    @classmethod
    def is_monitoring_category(cls, category: EnumResultCategory) -> bool:
        """Check if the category is for monitoring purposes."""
        return category in {
            cls.PERFORMANCE,
            cls.SECURITY,
            cls.AUDIT,
            cls.DEBUG,
        }


# Export for use
__all__ = ["EnumResultCategory"]
