"""
Metadata tool complexity enumeration.

Defines complexity levels for metadata tools to help categorize their operational
and implementation complexity.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetadataToolComplexity(StrValueHelper, str, Enum):
    """
    Complexity levels for metadata tools.

    Used to categorize metadata tools by their operational complexity,
    implementation difficulty, and resource requirements.
    """

    # Standard complexity levels
    SIMPLE = "simple"  # Straightforward operations, minimal dependencies
    MODERATE = "moderate"  # Some dependencies, moderate logic complexity
    COMPLEX = "complex"  # Multiple dependencies, complex logic flows
    ADVANCED = "advanced"  # Advanced patterns, high resource requirements

    @classmethod
    def get_numeric_level(cls, complexity: EnumMetadataToolComplexity) -> int:
        """
        Get numeric representation of complexity level (1-4).

        Args:
            complexity: The complexity level to convert

        Returns:
            Numeric value from 1 (simple) to 4 (advanced)
        """
        mapping = {
            cls.SIMPLE: 1,
            cls.MODERATE: 2,
            cls.COMPLEX: 3,
            cls.ADVANCED: 4,
        }
        return mapping.get(complexity, 1)

    @classmethod
    def is_simple(cls, complexity: EnumMetadataToolComplexity) -> bool:
        """
        Check if complexity level is simple.

        Args:
            complexity: The complexity level to check

        Returns:
            True if complexity is SIMPLE
        """
        return complexity == cls.SIMPLE

    @classmethod
    def requires_advanced_knowledge(
        cls, complexity: EnumMetadataToolComplexity
    ) -> bool:
        """
        Check if complexity level requires advanced knowledge.

        Args:
            complexity: The complexity level to check

        Returns:
            True if complexity is COMPLEX or ADVANCED
        """
        return complexity in {cls.COMPLEX, cls.ADVANCED}

    @classmethod
    def get_description(cls, complexity: EnumMetadataToolComplexity) -> str:
        """
        Get human-readable description of complexity level.

        Args:
            complexity: The complexity level to describe

        Returns:
            Description of the complexity level
        """
        descriptions = {
            cls.SIMPLE: "Simple tool with straightforward operations and minimal dependencies",
            cls.MODERATE: "Moderate complexity with some dependencies and logic flows",
            cls.COMPLEX: "Complex tool with multiple dependencies and intricate logic",
            cls.ADVANCED: "Advanced tool requiring expert knowledge and significant resources",
        }
        return descriptions.get(
            complexity,
            "Unknown complexity level",
        )

    @classmethod
    def get_default_level(cls) -> EnumMetadataToolComplexity:
        """
        Get the default complexity level.

        Returns:
            Default complexity level (SIMPLE)
        """
        return cls.SIMPLE


# Export the enum
__all__ = ["EnumMetadataToolComplexity"]
