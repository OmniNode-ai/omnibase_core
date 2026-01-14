"""
Documentation quality enumeration.

Defines quality levels for documentation assessment.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDocumentationQuality(StrValueHelper, str, Enum):
    """
    Enumeration of documentation quality levels.

    Used to assess and categorize the quality of documentation.
    """

    # Quality levels from poor to excellent
    NONE = "none"
    POOR = "poor"
    MINIMAL = "minimal"
    BASIC = "basic"
    ADEQUATE = "adequate"
    GOOD = "good"
    COMPREHENSIVE = "comprehensive"
    EXCELLENT = "excellent"
    OUTSTANDING = "outstanding"

    # Special categories
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"

    @classmethod
    def get_numeric_score(cls, quality: EnumDocumentationQuality) -> int:
        """Get numeric quality score (0-10)."""
        mapping = {
            cls.NONE: 0,
            cls.MISSING: 0,
            cls.POOR: 1,
            cls.MINIMAL: 2,
            cls.INCOMPLETE: 3,
            cls.BASIC: 4,
            cls.ADEQUATE: 5,
            cls.OUTDATED: 4,  # Good content but not current
            cls.GOOD: 6,
            cls.COMPREHENSIVE: 8,
            cls.EXCELLENT: 9,
            cls.OUTSTANDING: 10,
            cls.UNKNOWN: 5,  # Default middle score
        }
        return mapping.get(quality, 5)

    @classmethod
    def is_acceptable(cls, quality: EnumDocumentationQuality) -> bool:
        """Check if documentation quality is acceptable."""
        return quality in {
            cls.ADEQUATE,
            cls.GOOD,
            cls.COMPREHENSIVE,
            cls.EXCELLENT,
            cls.OUTSTANDING,
        }

    @classmethod
    def needs_improvement(cls, quality: EnumDocumentationQuality) -> bool:
        """Check if documentation needs improvement."""
        return quality in {
            cls.NONE,
            cls.POOR,
            cls.MINIMAL,
            cls.BASIC,
            cls.MISSING,
            cls.INCOMPLETE,
            cls.OUTDATED,
        }

    @classmethod
    def is_high_quality(cls, quality: EnumDocumentationQuality) -> bool:
        """Check if documentation is high quality."""
        return quality in {
            cls.COMPREHENSIVE,
            cls.EXCELLENT,
            cls.OUTSTANDING,
        }

    @classmethod
    def get_improvement_suggestion(cls, quality: EnumDocumentationQuality) -> str:
        """Get improvement suggestion for quality level."""
        suggestions = {
            cls.NONE: "Create basic documentation with purpose and usage",
            cls.MISSING: "Add documentation files and basic content",
            cls.POOR: "Improve clarity and add more details",
            cls.MINIMAL: "Expand with examples and use cases",
            cls.BASIC: "Add more detailed explanations and edge cases",
            cls.INCOMPLETE: "Complete missing sections and examples",
            cls.OUTDATED: "Update documentation to reflect current state",
            cls.ADEQUATE: "Enhance with more examples and best practices",
            cls.GOOD: "Consider adding advanced topics and tutorials",
            cls.COMPREHENSIVE: "Maintain current quality and keep updated",
            cls.EXCELLENT: "Continue maintaining high standards",
            cls.OUTSTANDING: "Serve as example for other documentation",
            cls.UNKNOWN: "Assess current documentation and identify needs",
        }
        return suggestions.get(quality, "Review and assess documentation needs")

    @classmethod
    def from_score(cls, score: int) -> EnumDocumentationQuality:
        """Convert numeric score (0-10) to quality level."""
        # Threshold-based quality mapping - architectural design for clear boundaries
        if score <= 0:
            return cls.NONE
        if score <= 1:
            return cls.POOR
        if score <= 2:
            return cls.MINIMAL
        if score <= 3:
            return cls.BASIC
        if score <= 4:
            return cls.ADEQUATE
        if score <= 6:
            return cls.GOOD
        if score <= 8:
            return cls.COMPREHENSIVE
        if score <= 9:
            return cls.EXCELLENT
        return cls.OUTSTANDING


# Export the enum
__all__ = ["EnumDocumentationQuality"]
