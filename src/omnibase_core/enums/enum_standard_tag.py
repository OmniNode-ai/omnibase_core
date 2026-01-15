"""
Standard Tag Enum.

Standardized tags for consistent classification across metadata models.
Reduces reliance on free-form string tags while maintaining extensibility.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStandardTag(StrValueHelper, str, Enum):
    """
    Standard tags for metadata classification.

    Provides consistent tagging across all metadata models while reducing
    the need for free-form string tags.
    """

    # Functional tags
    CORE = "core"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
    STABLE = "stable"
    LEGACY = "legacy"

    # Complexity tags
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"

    # Domain tags
    API = "api"
    UI = "ui"
    DATABASE = "database"
    SECURITY = "security"
    PERFORMANCE = "performance"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"

    # Quality tags
    TESTED = "tested"
    DOCUMENTED = "documented"
    REVIEWED = "reviewed"
    OPTIMIZED = "optimized"
    MONITORED = "monitored"

    # Usage tags
    HIGH_TRAFFIC = "high_traffic"
    LOW_LATENCY = "low_latency"
    BATCH_PROCESSING = "batch_processing"
    REAL_TIME = "real_time"
    BACKGROUND = "background"

    # Integration tags
    EXTERNAL = "external"
    INTERNAL = "internal"
    THIRD_PARTY = "third_party"
    CUSTOM = "custom"

    @classmethod
    def get_functional_tags(cls) -> list[EnumStandardTag]:
        """Get all functional classification tags."""
        return [
            cls.CORE,
            cls.EXPERIMENTAL,
            cls.DEPRECATED,
            cls.STABLE,
            cls.LEGACY,
        ]

    @classmethod
    def get_complexity_tags(cls) -> list[EnumStandardTag]:
        """Get all complexity classification tags."""
        return [
            cls.SIMPLE,
            cls.MODERATE,
            cls.COMPLEX,
            cls.ADVANCED,
        ]

    @classmethod
    def get_domain_tags(cls) -> list[EnumStandardTag]:
        """Get all domain classification tags."""
        return [
            cls.API,
            cls.UI,
            cls.DATABASE,
            cls.SECURITY,
            cls.PERFORMANCE,
            cls.VALIDATION,
            cls.TRANSFORMATION,
        ]

    @classmethod
    def get_quality_tags(cls) -> list[EnumStandardTag]:
        """Get all quality classification tags."""
        return [
            cls.TESTED,
            cls.DOCUMENTED,
            cls.REVIEWED,
            cls.OPTIMIZED,
            cls.MONITORED,
        ]

    @classmethod
    def from_string(cls, value: str) -> EnumStandardTag | None:
        """Convert string to standard tag with fallback handling."""
        # Direct mapping
        for tag in cls:
            if tag.value == value.lower():
                return tag

        # Common aliases
        aliases = {
            "basic": cls.SIMPLE,
            "standard": cls.MODERATE,
            "high": cls.COMPLEX,
            "expert": cls.ADVANCED,
            "rest": cls.API,
            "frontend": cls.UI,
            "backend": cls.API,
            "db": cls.DATABASE,
            "auth": cls.SECURITY,
            "perf": cls.PERFORMANCE,
            "valid": cls.VALIDATION,
            "transform": cls.TRANSFORMATION,
            "external_api": cls.EXTERNAL,
            "internal_api": cls.INTERNAL,
        }

        normalized = value.lower().strip()
        return aliases.get(normalized)

    @property
    def category(self) -> str:
        """Get the category this tag belongs to."""
        if self in self.get_functional_tags():
            return "functional"
        if self in self.get_complexity_tags():
            return "complexity"
        if self in self.get_domain_tags():
            return "domain"
        if self in self.get_quality_tags():
            return "quality"
        return "other"


# Export for use
__all__ = ["EnumStandardTag"]
