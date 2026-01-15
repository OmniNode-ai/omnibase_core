"""
Standard Category Enum.

Standardized categories for consistent classification across metadata models.
Provides hierarchical organization beyond simple tags.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStandardCategory(StrValueHelper, str, Enum):
    """
    Standard categories for metadata classification.

    Provides hierarchical organization and consistent categorization
    across all metadata models.
    """

    # ModelArchitecture categories
    EFFECT = "effect"
    COMPUTE = "compute"
    REDUCER = "reducer"
    ORCHESTRATOR = "orchestrator"

    # Functional categories
    DATA_PROCESSING = "data_processing"
    BUSINESS_LOGIC = "business_logic"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    USER_INTERFACE = "user_interface"

    # Domain categories
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ANALYTICS = "analytics"
    MONITORING = "monitoring"
    CONFIGURATION = "configuration"

    # EnumLifecycle categories
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    DOCUMENTATION = "documentation"

    # Quality categories
    PERFORMANCE = "performance"
    SECURITY = "security"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    USABILITY = "usability"

    # Data categories
    INPUT = "input"
    OUTPUT = "output"
    STORAGE = "storage"
    STREAMING = "streaming"
    BATCH = "batch"

    @classmethod
    def get_architecture_categories(cls) -> list[EnumStandardCategory]:
        """Get ONEX 4-node architecture categories."""
        return [
            cls.EFFECT,
            cls.COMPUTE,
            cls.REDUCER,
            cls.ORCHESTRATOR,
        ]

    @classmethod
    def get_functional_categories(cls) -> list[EnumStandardCategory]:
        """Get functional classification categories."""
        return [
            cls.DATA_PROCESSING,
            cls.BUSINESS_LOGIC,
            cls.INTEGRATION,
            cls.INFRASTRUCTURE,
            cls.USER_INTERFACE,
        ]

    @classmethod
    def get_domain_categories(cls) -> list[EnumStandardCategory]:
        """Get domain-specific categories."""
        return [
            cls.AUTHENTICATION,
            cls.AUTHORIZATION,
            cls.VALIDATION,
            cls.TRANSFORMATION,
            cls.ANALYTICS,
            cls.MONITORING,
            cls.CONFIGURATION,
        ]

    @classmethod
    def get_lifecycle_categories(cls) -> list[EnumStandardCategory]:
        """Get lifecycle stage categories."""
        return [
            cls.DEVELOPMENT,
            cls.TESTING,
            cls.STAGING,
            cls.PRODUCTION,
            cls.MAINTENANCE,
            cls.DOCUMENTATION,
        ]

    @classmethod
    def get_quality_categories(cls) -> list[EnumStandardCategory]:
        """Get quality attribute categories."""
        return [
            cls.PERFORMANCE,
            cls.SECURITY,
            cls.RELIABILITY,
            cls.SCALABILITY,
            cls.USABILITY,
        ]

    @classmethod
    def get_data_categories(cls) -> list[EnumStandardCategory]:
        """Get data processing categories."""
        return [
            cls.INPUT,
            cls.OUTPUT,
            cls.STORAGE,
            cls.STREAMING,
            cls.BATCH,
        ]

    @classmethod
    def from_string(cls, value: str) -> EnumStandardCategory | None:
        """Convert string to standard category with fallback handling."""
        # Category alias mapping - architectural design for category classification
        # Direct mapping
        for category in cls:
            if category.value == value.lower():
                return category

        # Common aliases
        aliases = {
            "auth": cls.AUTHENTICATION,
            "authz": cls.AUTHORIZATION,
            "valid": cls.VALIDATION,
            "transform": cls.TRANSFORMATION,
            "config": cls.CONFIGURATION,
            "dev": cls.DEVELOPMENT,
            "test": cls.TESTING,
            "prod": cls.PRODUCTION,
            "perf": cls.PERFORMANCE,
            "sec": cls.SECURITY,
            "ui": cls.USER_INTERFACE,
            "api": cls.INTEGRATION,
            "data": cls.DATA_PROCESSING,
            "business": cls.BUSINESS_LOGIC,
            "infra": cls.INFRASTRUCTURE,
        }

        normalized = value.lower().strip()
        return aliases.get(normalized)

    @property
    def hierarchy_level(self) -> str:
        """Get the hierarchy level this category belongs to."""
        if self in self.get_architecture_categories():
            return "architecture"
        if self in self.get_functional_categories():
            return "functional"
        if self in self.get_domain_categories():
            return "domain"
        if self in self.get_lifecycle_categories():
            return "lifecycle"
        if self in self.get_quality_categories():
            return "quality"
        if self in self.get_data_categories():
            return "data"
        return "other"

    @property
    def is_onex_architecture(self) -> bool:
        """Check if this is an ONEX 4-node architecture category."""
        return self in self.get_architecture_categories()

    @property
    def is_quality_focused(self) -> bool:
        """Check if this is a quality-focused category."""
        return self in self.get_quality_categories()


# Export for use
__all__ = ["EnumStandardCategory"]
