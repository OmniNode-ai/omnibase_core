"""
Conceptual complexity enumeration for skill level and understanding requirements.

Focused on cognitive difficulty, learning curve, and expertise requirements.
Part of the unified complexity enum consolidation strategy.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConceptualComplexity(StrValueHelper, str, Enum):
    """
    Conceptual complexity levels for understanding and skill requirements.

    Focuses on cognitive difficulty, expertise requirements, and learning curve
    rather than operational or performance characteristics.
    """

    # Skill and understanding levels
    TRIVIAL = "trivial"  # No special knowledge required
    BASIC = "basic"  # Basic understanding sufficient
    INTERMEDIATE = "intermediate"  # Moderate domain knowledge required
    ADVANCED = "advanced"  # Deep expertise required
    EXPERT = "expert"  # Expert-level knowledge required

    @classmethod
    def get_numeric_value(cls, level: EnumConceptualComplexity) -> int:
        """Get numeric representation of conceptual complexity level (1-5)."""
        mapping = {
            cls.TRIVIAL: 1,
            cls.BASIC: 2,
            cls.INTERMEDIATE: 3,
            cls.ADVANCED: 4,
            cls.EXPERT: 5,
        }
        return mapping.get(level, 3)

    @classmethod
    def is_beginner_friendly(cls, level: EnumConceptualComplexity) -> bool:
        """Check if conceptual complexity is accessible to beginners."""
        return level in {cls.TRIVIAL, cls.BASIC}

    @classmethod
    def requires_expertise(cls, level: EnumConceptualComplexity) -> bool:
        """Check if conceptual complexity requires expert knowledge."""
        return level in {cls.ADVANCED, cls.EXPERT}

    @classmethod
    def get_skill_requirement(cls, level: EnumConceptualComplexity) -> str:
        """Get skill requirement description for conceptual complexity."""
        skill_map = {
            cls.TRIVIAL: "No special skills required",
            cls.BASIC: "Basic domain knowledge",
            cls.INTERMEDIATE: "Solid understanding required",
            cls.ADVANCED: "Deep expertise needed",
            cls.EXPERT: "Expert-level mastery required",
        }
        return skill_map.get(level, "Moderate knowledge required")

    @classmethod
    def get_learning_time_estimate(cls, level: EnumConceptualComplexity) -> str:
        """Get estimated learning time for conceptual complexity."""
        time_map = {
            cls.TRIVIAL: "< 1 hour",
            cls.BASIC: "1-8 hours",
            cls.INTERMEDIATE: "1-4 weeks",
            cls.ADVANCED: "1-6 months",
            cls.EXPERT: "6+ months",
        }
        return time_map.get(level, "Variable")


# Export for use
__all__ = ["EnumConceptualComplexity"]
