"""
Document Freshness Actions enum for type-safe action resolution.

This enum provides compile-time safety and eliminates magic strings
for document freshness monitoring actions.
"""

from enum import Enum, unique


@unique
class EnumDocumentFreshnessActions(str, Enum):
    """
    Canonical enumeration of all document freshness monitoring actions.

    Use these enum values instead of string literals for type safety
    and compile-time validation of action names.
    """

    MONITOR_FRESHNESS = "monitor_freshness"
    ANALYZE_DEPENDENCIES = "analyze_dependencies"
    DETECT_CHANGES = "detect_changes"
    AI_SEMANTIC_ANALYSIS = "ai_semantic_analysis"
    GENERATE_AUDIT_REPORT = "generate_audit_report"
    HEALTH_CHECK = "health_check"
    CONNECTION_POOL_METRICS = "connection_pool_metrics"


@unique
class EnumDocumentFreshnessRiskLevel(str, Enum):
    """Risk levels for document freshness assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@unique
class EnumDocumentFreshnessStatus(str, Enum):
    """Overall freshness status values."""

    FRESH = "fresh"
    STALE = "stale"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@unique
class EnumDocumentType(str, Enum):
    """Document type classifications."""

    DOCUMENT = "document"
    CODE = "code"
    CONFIG = "config"
    DATA = "data"


@unique
class EnumRecommendationType(str, Enum):
    """Recommendation types for document improvements."""

    UPDATE_REQUIRED = "update_required"
    REVIEW_SUGGESTED = "review_suggested"
    DEPRECATION_WARNING = "deprecation_warning"
    OPTIMIZATION = "optimization"


@unique
class EnumRecommendationPriority(str, Enum):
    """Priority levels for recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@unique
class EnumEstimatedEffort(str, Enum):
    """Estimated effort levels for implementing recommendations."""

    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


@unique
class EnumDependencyRelationship(str, Enum):
    """Types of dependency relationships between documents."""

    IMPORTS = "imports"
    REFERENCES = "references"
    INCLUDES = "includes"
    DEPENDS_ON = "depends_on"


@unique
class EnumOutputFormat(str, Enum):
    """Output format options for analysis results."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
