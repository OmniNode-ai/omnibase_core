from __future__ import annotations

"""
Configuration category enumeration for categorizing system configurations.

Provides strongly typed categories for various configuration types
across the ONEX architecture.
"""


from enum import Enum, unique


@unique
class EnumConfigCategory(str, Enum):
    """
    Strongly typed configuration categories.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for configuration categorization.
    """

    # Core system categories
    GENERATION = "generation"
    VALIDATION = "validation"
    TEMPLATE = "template"
    MAINTENANCE = "maintenance"
    RUNTIME = "runtime"

    # Infrastructure categories
    CLI = "cli"
    DISCOVERY = "discovery"
    SCHEMA = "schema"
    LOGGING = "logging"
    TESTING = "testing"

    # Generic categories
    GENERAL = "general"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_system_categories(cls) -> list[EnumConfigCategory]:
        """Get core system configuration categories."""
        return [
            cls.GENERATION,
            cls.VALIDATION,
            cls.TEMPLATE,
            cls.MAINTENANCE,
            cls.RUNTIME,
        ]

    @classmethod
    def get_infrastructure_categories(cls) -> list[EnumConfigCategory]:
        """Get infrastructure configuration categories."""
        return [
            cls.CLI,
            cls.DISCOVERY,
            cls.SCHEMA,
            cls.LOGGING,
            cls.TESTING,
        ]

    @classmethod
    def is_system_category(cls, category: EnumConfigCategory) -> bool:
        """Check if category is a core system category."""
        return category in cls.get_system_categories()

    @classmethod
    def is_infrastructure_category(cls, category: EnumConfigCategory) -> bool:
        """Check if category is an infrastructure category."""
        return category in cls.get_infrastructure_categories()


# Export for use
__all__ = ["EnumConfigCategory"]
