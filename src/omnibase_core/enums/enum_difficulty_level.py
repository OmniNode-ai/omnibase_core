"""
Difficulty level enumeration.

Defines difficulty levels for examples and learning materials.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDifficultyLevel(StrValueHelper, str, Enum):
    """
    Enumeration of difficulty levels for examples and tutorials.

    Used for categorizing learning materials and examples by complexity.
    """

    # Standard difficulty levels
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    # Additional granular levels
    NOVICE = "novice"
    EXPERT = "expert"

    @classmethod
    def get_numeric_level(cls, difficulty: EnumDifficultyLevel) -> int:
        """Get numeric representation of difficulty level (1-5)."""
        mapping = {
            cls.NOVICE: 1,
            cls.BEGINNER: 2,
            cls.INTERMEDIATE: 3,
            cls.ADVANCED: 4,
            cls.EXPERT: 5,
        }
        return mapping.get(difficulty, 2)

    @classmethod
    def is_beginner_friendly(cls, difficulty: EnumDifficultyLevel) -> bool:
        """Check if difficulty level is suitable for beginners."""
        return difficulty in {cls.NOVICE, cls.BEGINNER}

    @classmethod
    def requires_experience(cls, difficulty: EnumDifficultyLevel) -> bool:
        """Check if difficulty level requires prior experience."""
        return difficulty in {cls.ADVANCED, cls.EXPERT}

    @classmethod
    def get_recommended_prerequisites(
        cls,
        difficulty: EnumDifficultyLevel,
    ) -> list[str]:
        """Get recommended prerequisites for difficulty level."""
        prerequisites: dict[EnumDifficultyLevel, list[str]] = {
            cls.NOVICE: [],
            cls.BEGINNER: ["Basic programming concepts"],
            cls.INTERMEDIATE: ["Programming fundamentals", "Basic frameworks"],
            cls.ADVANCED: ["Solid programming experience", "Framework expertise"],
            cls.EXPERT: [
                "Expert-level programming",
                "ModelArchitecture knowledge",
                "Advanced patterns",
            ],
        }
        return prerequisites.get(difficulty, [])

    @classmethod
    def get_default_level(cls) -> EnumDifficultyLevel:
        """Get the default difficulty level."""
        return cls.BEGINNER


# Export the enum
__all__ = ["EnumDifficultyLevel"]
