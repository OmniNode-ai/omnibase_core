"""
Example category enumeration for example classification.

Provides strongly typed example category values for example organization and retrieval.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumExampleCategory(str, Enum):
    """
    Strongly typed example category for example classification.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    BASIC = "basic"
    ADVANCED = "advanced"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    DEMO = "demo"
    TEMPLATE = "template"
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"
    TESTING = "testing"
    DEBUGGING = "debugging"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MIGRATION = "migration"
    EXPERIMENTAL = "experimental"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_educational(cls, category: "EnumExampleCategory") -> bool:
        """Check if the example category is educational."""
        return category in {cls.BASIC, cls.ADVANCED, cls.TUTORIAL, cls.DEMO}

    @classmethod
    def is_practical(cls, category: "EnumExampleCategory") -> bool:
        """Check if the example category is practical."""
        return category in {cls.TEMPLATE, cls.INTEGRATION, cls.CONFIGURATION, cls.MIGRATION}

    @classmethod
    def is_quality_focused(cls, category: "EnumExampleCategory") -> bool:
        """Check if the example category is quality-focused."""
        return category in {cls.BEST_PRACTICE, cls.ANTI_PATTERN, cls.TESTING, cls.SECURITY}

    @classmethod
    def is_technical(cls, category: "EnumExampleCategory") -> bool:
        """Check if the example category is technical."""
        return category in {cls.DEBUGGING, cls.PERFORMANCE, cls.TESTING, cls.INTEGRATION}

    @classmethod
    def requires_expertise(cls, category: "EnumExampleCategory") -> bool:
        """Check if the example category requires expertise."""
        return category in {cls.ADVANCED, cls.PERFORMANCE, cls.SECURITY, cls.MIGRATION, cls.EXPERIMENTAL}

    @classmethod
    def is_reference_material(cls, category: "EnumExampleCategory") -> bool:
        """Check if the example category is reference material."""
        return category in {cls.REFERENCE, cls.TEMPLATE, cls.BEST_PRACTICE, cls.ANTI_PATTERN}


# Export for use
__all__ = ["EnumExampleCategory"]