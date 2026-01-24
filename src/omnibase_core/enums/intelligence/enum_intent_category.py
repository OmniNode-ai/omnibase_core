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

from omnibase_core.utils.util_str_enum_base import StrValueHelper

# Module-level cached frozensets (populated after class definition)
# These are initialized once and reused for all calls to the classmethod accessors.
_DEVELOPMENT_INTENTS: frozenset[EnumIntentCategory] | None = None
_INTELLIGENCE_INTENTS: frozenset[EnumIntentCategory] | None = None
_META_INTENTS: frozenset[EnumIntentCategory] | None = None


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
    # so we use @classmethod with module-level cached frozensets. The frozensets
    # are lazily initialized on first access and reused for all subsequent calls.

    @classmethod
    def _development_intents(cls) -> frozenset[EnumIntentCategory]:
        """Internal: Development intent category group (cached)."""
        global _DEVELOPMENT_INTENTS
        if _DEVELOPMENT_INTENTS is None:
            _DEVELOPMENT_INTENTS = frozenset(
                {
                    cls.CODE_GENERATION,
                    cls.DEBUGGING,
                    cls.REFACTORING,
                    cls.TESTING,
                    cls.DOCUMENTATION,
                    cls.ANALYSIS,
                }
            )
        return _DEVELOPMENT_INTENTS

    @classmethod
    def _intelligence_intents(cls) -> frozenset[EnumIntentCategory]:
        """Internal: Intelligence/ML intent category group (cached)."""
        global _INTELLIGENCE_INTENTS
        if _INTELLIGENCE_INTENTS is None:
            _INTELLIGENCE_INTENTS = frozenset(
                {
                    cls.PATTERN_LEARNING,
                    cls.QUALITY_ASSESSMENT,
                    cls.SEMANTIC_ANALYSIS,
                }
            )
        return _INTELLIGENCE_INTENTS

    @classmethod
    def _meta_intents(cls) -> frozenset[EnumIntentCategory]:
        """Internal: Meta/system interaction intent category group (cached)."""
        global _META_INTENTS
        if _META_INTENTS is None:
            _META_INTENTS = frozenset(
                {
                    cls.HELP,
                    cls.CLARIFY,
                    cls.FEEDBACK,
                }
            )
        return _META_INTENTS

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
        return category in cls._development_intents()

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
        return category in cls._intelligence_intents()

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
        return category in cls._meta_intents()

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
        return set(cls._development_intents())

    @classmethod
    def get_intelligence_intents(cls) -> set[EnumIntentCategory]:
        """Get all intelligence/ML-focused intent categories.

        Returns:
            Set of intelligence intent categories.
        """
        return set(cls._intelligence_intents())

    @classmethod
    def get_meta_intents(cls) -> set[EnumIntentCategory]:
        """Get all meta/system interaction intent categories.

        Returns:
            Set of meta intent categories.
        """
        return set(cls._meta_intents())


__all__ = ["EnumIntentCategory"]
