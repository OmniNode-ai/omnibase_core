"""Intent category enumeration for classification.

Defines canonical intent categories used across the OmniNode intelligence
ecosystem. These categories represent high-level user intent types that
can be detected from text, code, or interaction patterns.

Categorization Scheme:
    - Development intents: Code-focused activities (generation, debugging, etc.)
    - Intelligence intents: ML/AI-focused activities (pattern learning, etc.)
    - Meta intents: System interaction (help, clarification, feedback)

This enum is storage-agnostic and can be used with any persistence layer
or classification algorithm.
"""

from __future__ import annotations

from enum import Enum, unique
from functools import lru_cache

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumIntentCategory(StrValueHelper, str, Enum):
    """Canonical intent categories for classification.

    These categories represent high-level user intent types that can be
    detected across different interaction contexts (CLI, chat, code analysis).
    Values use snake_case to match the existing omniintelligence patterns.

    Category Groups:
        - Development: CODE_GENERATION, DEBUGGING, REFACTORING, TESTING,
          DOCUMENTATION, ANALYSIS
        - Intelligence: PATTERN_LEARNING, QUALITY_ASSESSMENT, SEMANTIC_ANALYSIS
        - Meta: HELP, CLARIFY, FEEDBACK
        - Fallback: UNKNOWN

    Helper Methods:
        - is_development_intent(): Check if category is development-focused
        - is_intelligence_intent(): Check if category is intelligence/ML-focused
        - is_meta_intent(): Check if category is about system interaction
        - is_classified(): Check if category has been successfully classified
    """

    # =========================================================================
    # Development Intents - Code-focused activities
    # =========================================================================

    CODE_GENERATION = "code_generation"
    """Generating new code, functions, classes, or modules."""

    DEBUGGING = "debugging"
    """Diagnosing and fixing bugs, errors, or issues."""

    REFACTORING = "refactoring"
    """Improving code structure, performance, or readability."""

    TESTING = "testing"
    """Creating or running tests, validation, or verification."""

    DOCUMENTATION = "documentation"
    """Creating or updating documentation, comments, or guides."""

    ANALYSIS = "analysis"
    """Reviewing, inspecting, or evaluating code or systems."""

    # =========================================================================
    # Intelligence Intents - ML/AI-focused activities
    # =========================================================================

    PATTERN_LEARNING = "pattern_learning"
    """Learning patterns from code, extracting features, or training models."""

    QUALITY_ASSESSMENT = "quality_assessment"
    """Assessing code quality, compliance, or standards adherence."""

    SEMANTIC_ANALYSIS = "semantic_analysis"
    """Extracting semantic meaning, concepts, or domain knowledge."""

    # =========================================================================
    # Meta Intents - System interaction
    # =========================================================================

    HELP = "help"
    """Requesting assistance or information about capabilities."""

    CLARIFY = "clarify"
    """Seeking clarification on previous responses or instructions."""

    FEEDBACK = "feedback"
    """Providing feedback on results, quality, or behavior."""

    # =========================================================================
    # Fallback
    # =========================================================================

    UNKNOWN = "unknown"
    """Intent could not be determined or does not match any known category."""

    # =========================================================================
    # Internal Category Group Constants (Single Source of Truth)
    # =========================================================================
    # NOTE: Python enums cannot have class attributes that aren't enum members,
    # so we use @staticmethod with @lru_cache for thread-safe, lazy caching.
    # The frozensets are computed once on first access and cached automatically.

    @staticmethod
    @lru_cache(maxsize=1)
    def _development_intents() -> frozenset[EnumIntentCategory]:
        """Internal: Development intent category group (cached)."""
        return frozenset(
            {
                EnumIntentCategory.CODE_GENERATION,
                EnumIntentCategory.DEBUGGING,
                EnumIntentCategory.REFACTORING,
                EnumIntentCategory.TESTING,
                EnumIntentCategory.DOCUMENTATION,
                EnumIntentCategory.ANALYSIS,
            }
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def _intelligence_intents() -> frozenset[EnumIntentCategory]:
        """Internal: Intelligence/ML intent category group (cached)."""
        return frozenset(
            {
                EnumIntentCategory.PATTERN_LEARNING,
                EnumIntentCategory.QUALITY_ASSESSMENT,
                EnumIntentCategory.SEMANTIC_ANALYSIS,
            }
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def _meta_intents() -> frozenset[EnumIntentCategory]:
        """Internal: Meta/system interaction intent category group (cached)."""
        return frozenset(
            {
                EnumIntentCategory.HELP,
                EnumIntentCategory.CLARIFY,
                EnumIntentCategory.FEEDBACK,
            }
        )

    # =========================================================================
    # Classification Checker Methods
    # =========================================================================

    @classmethod
    def is_development_intent(cls, category: EnumIntentCategory) -> bool:
        """Check if the category is a development-focused intent.

        Development intents involve code creation, modification, or analysis.

        Args:
            category: The intent category to check.

        Returns:
            True if the category is development-focused.
        """
        return category in EnumIntentCategory._development_intents()

    @classmethod
    def is_intelligence_intent(cls, category: EnumIntentCategory) -> bool:
        """Check if the category is an intelligence/ML-focused intent.

        Intelligence intents involve machine learning, pattern extraction,
        or semantic understanding.

        Args:
            category: The intent category to check.

        Returns:
            True if the category is intelligence-focused.
        """
        return category in EnumIntentCategory._intelligence_intents()

    @classmethod
    def is_meta_intent(cls, category: EnumIntentCategory) -> bool:
        """Check if the category is a meta/system interaction intent.

        Meta intents are about interacting with the system itself rather
        than performing a specific task.

        Args:
            category: The intent category to check.

        Returns:
            True if the category is a meta intent.
        """
        return category in EnumIntentCategory._meta_intents()

    @classmethod
    def is_classified(cls, category: EnumIntentCategory) -> bool:
        """Check if the category represents a successful classification.

        Args:
            category: The intent category to check.

        Returns:
            True if the category is not UNKNOWN (i.e., was classified).
        """
        return category != cls.UNKNOWN

    # =========================================================================
    # Category Group Getter Methods
    # =========================================================================

    @classmethod
    def get_development_intents(cls) -> set[EnumIntentCategory]:
        """Get all development-focused intent categories.

        Returns:
            Set of development intent categories.
        """
        return set(EnumIntentCategory._development_intents())

    @classmethod
    def get_intelligence_intents(cls) -> set[EnumIntentCategory]:
        """Get all intelligence/ML-focused intent categories.

        Returns:
            Set of intelligence intent categories.
        """
        return set(EnumIntentCategory._intelligence_intents())

    @classmethod
    def get_meta_intents(cls) -> set[EnumIntentCategory]:
        """Get all meta/system interaction intent categories.

        Returns:
            Set of meta intent categories.
        """
        return set(EnumIntentCategory._meta_intents())


__all__ = ["EnumIntentCategory"]
