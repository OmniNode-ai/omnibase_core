"""
Collection purpose enumeration.

Defines purposes for data collections and analytics.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCollectionPurpose(StrValueHelper, str, Enum):
    """
    Enumeration of collection purposes.

    Used to categorize the intended use of data collections.
    """

    # General purposes
    GENERAL = "general"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    MONITORING = "monitoring"
    TESTING = "testing"
    VALIDATION = "validation"

    # Development purposes
    DEVELOPMENT = "development"
    DEBUGGING = "debugging"
    BENCHMARKING = "benchmarking"
    PROFILING = "profiling"

    # Business purposes
    BUSINESS_INTELLIGENCE = "business_intelligence"
    COMPLIANCE = "compliance"
    AUDIT = "audit"
    RESEARCH = "research"

    # Data purposes
    BACKUP = "backup"
    ARCHIVAL = "archival"
    MIGRATION = "migration"
    SYNCHRONIZATION = "synchronization"

    # Processing purposes
    BATCH_PROCESSING = "batch_processing"
    REAL_TIME_PROCESSING = "real_time_processing"
    STREAMING = "streaming"
    ETL = "etl"

    # Special purposes
    TEMPORARY = "temporary"
    EXPERIMENTAL = "experimental"
    CACHE = "cache"
    CONFIGURATION = "configuration"
    METADATA = "metadata"

    # Unknown/unspecified
    UNKNOWN = "unknown"
    CUSTOM = "custom"

    @classmethod
    def is_analytical_purpose(cls, purpose: EnumCollectionPurpose) -> bool:
        """Check if purpose is for analytical use."""
        return purpose in {
            cls.ANALYSIS,
            cls.REPORTING,
            cls.BUSINESS_INTELLIGENCE,
            cls.RESEARCH,
            cls.BENCHMARKING,
            cls.PROFILING,
        }

    @classmethod
    def is_operational_purpose(cls, purpose: EnumCollectionPurpose) -> bool:
        """Check if purpose is for operational use."""
        return purpose in {
            cls.MONITORING,
            cls.REAL_TIME_PROCESSING,
            cls.STREAMING,
            cls.SYNCHRONIZATION,
            cls.CACHE,
        }

    @classmethod
    def is_compliance_purpose(cls, purpose: EnumCollectionPurpose) -> bool:
        """Check if purpose is for compliance."""
        return purpose in {
            cls.COMPLIANCE,
            cls.AUDIT,
            cls.ARCHIVAL,
            cls.BACKUP,
        }

    @classmethod
    def is_temporary_purpose(cls, purpose: EnumCollectionPurpose) -> bool:
        """Check if purpose is temporary."""
        return purpose in {
            cls.TEMPORARY,
            cls.EXPERIMENTAL,
            cls.TESTING,
            cls.DEBUGGING,
            cls.CACHE,
        }

    @classmethod
    def get_retention_suggestion(cls, purpose: EnumCollectionPurpose) -> str:
        """Get suggested retention policy for purpose."""
        if cls.is_compliance_purpose(purpose):
            return "long_term"
        if cls.is_temporary_purpose(purpose):
            return "short_term"
        if cls.is_analytical_purpose(purpose) or cls.is_operational_purpose(purpose):
            return "medium_term"
        return "default"


# Export the enum
__all__ = ["EnumCollectionPurpose"]
