"""
Document freshness models for tracking document staleness and relevance.

Defines core data structures for document freshness scoring, tracking,
and monitoring within the ONEX document management system.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class EnumDocumentType(str, Enum):
    """Document type classification for freshness analysis."""

    ARCHITECTURE = "architecture"
    API_DOCUMENTATION = "api_documentation"
    USER_GUIDE = "user_guide"
    TUTORIAL = "tutorial"
    README = "readme"
    CHANGELOG = "changelog"
    CONFIGURATION = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    DEVELOPER_NOTES = "developer_notes"
    BUSINESS_REQUIREMENTS = "business_requirements"
    TECHNICAL_SPECIFICATION = "technical_specification"
    DEPLOYMENT_GUIDE = "deployment_guide"
    UNKNOWN = "unknown"


class EnumFreshnessStatus(str, Enum):
    """Document freshness status levels."""

    FRESH = "fresh"  # Recently updated, no stale dependencies
    MODERATE = "moderate"  # Some age but still relevant
    STALE = "stale"  # Outdated, needs review
    CRITICAL = "critical"  # Severely outdated, urgent update needed
    UNKNOWN = "unknown"  # Unable to determine freshness


class EnumDocumentLifecycleState(str, Enum):
    """Document lifecycle states for automated management."""

    UP_TO_DATE = "up_to_date"
    LEGACY = "legacy"
    DEPRECATED = "deprecated"
    CANDIDATE_FOR_REMOVAL = "candidate_for_removal"
    BUSINESS_IDEAS = "business_ideas"
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"


class ModelDocumentDependency(ModelOnexInputState):
    """Represents a dependency relationship for document freshness tracking."""

    dependency_path: str = Field(
        ...,
        description="Path to the dependent file or resource",
    )
    dependency_type: str = Field(
        ...,
        description="Type of dependency (code, config, doc, external)",
    )
    last_modified: datetime = Field(
        ...,
        description="Last modification time of the dependency",
    )
    impact_weight: float = Field(
        default=1.0,
        description="Weight of this dependency on document freshness (0.0-1.0)",
    )
    is_critical: bool = Field(
        default=False,
        description="Whether this dependency is critical for document accuracy",
    )

    @validator("impact_weight")
    def validate_impact_weight(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "impact_weight must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelFreshnessScore(ModelOnexInputState):
    """Document freshness scoring result with detailed breakdown."""

    overall_score: float = Field(
        ...,
        description="Overall freshness score (0.0-1.0, higher is fresher)",
    )
    time_decay_score: float = Field(..., description="Score based on document age")
    dependency_score: float = Field(
        ...,
        description="Score based on dependency staleness",
    )
    semantic_drift_score: float = Field(
        default=1.0,
        description="Score based on semantic drift from code",
    )
    manual_override_score: float | None = Field(
        None,
        description="Manual override score if applicable",
    )

    # Score component weights
    time_weight: float = Field(
        default=0.4,
        description="Weight for time decay component",
    )
    dependency_weight: float = Field(
        default=0.4,
        description="Weight for dependency component",
    )
    semantic_weight: float = Field(
        default=0.2,
        description="Weight for semantic drift component",
    )

    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this score was calculated",
    )

    @validator(
        "overall_score",
        "time_decay_score",
        "dependency_score",
        "semantic_drift_score",
    )
    def validate_scores(self, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v

    @validator("time_weight", "dependency_weight", "semantic_weight")
    def validate_weights(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Weight must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDocumentFreshness(ModelOnexInputState):
    """Complete document freshness tracking information."""

    document_path: str = Field(..., description="Path to the document being tracked")
    document_type: EnumDocumentType = Field(
        ...,
        description="Classification of document type",
    )

    # Timestamps
    document_last_modified: datetime = Field(
        ...,
        description="Last modification time of the document",
    )
    last_freshness_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last time freshness was checked",
    )

    # Dependencies
    dependencies: list[ModelDocumentDependency] = Field(
        default_factory=list,
        description="List of tracked dependencies",
    )

    # Freshness assessment
    freshness_score: ModelFreshnessScore = Field(
        ...,
        description="Current freshness scoring breakdown",
    )
    freshness_status: EnumFreshnessStatus = Field(
        ...,
        description="Current freshness status level",
    )
    lifecycle_state: EnumDocumentLifecycleState = Field(
        default=EnumDocumentLifecycleState.UP_TO_DATE,
        description="Document lifecycle state",
    )

    # Metadata
    file_size_bytes: int = Field(default=0, description="Document file size in bytes")
    line_count: int | None = Field(None, description="Number of lines in document")
    word_count: int | None = Field(None, description="Estimated word count")

    # Tracking
    stale_dependency_count: int = Field(
        default=0,
        description="Number of stale dependencies detected",
    )
    critical_dependency_count: int = Field(
        default=0,
        description="Number of critical dependencies that are stale",
    )

    # Notifications
    notification_sent: bool = Field(
        default=False,
        description="Whether staleness notification has been sent",
    )
    notification_sent_at: datetime | None = Field(
        None,
        description="When notification was last sent",
    )

    # AI Analysis
    ai_analysis_enabled: bool = Field(
        default=False,
        description="Whether AI analysis is enabled for this document",
    )
    last_ai_analysis: datetime | None = Field(
        None,
        description="Last AI analysis timestamp",
    )
    ai_quality_score: float | None = Field(
        None,
        description="AI-assessed quality score (0.0-1.0)",
    )

    @validator("ai_quality_score")
    def validate_ai_quality_score(self, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "AI quality score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelFreshnessTimeThresholds(BaseModel):
    """Time-based thresholds for document freshness."""

    fresh: int = Field(..., description="Days threshold for fresh status")
    stale: int = Field(..., description="Days threshold for stale status")
    critical: int = Field(..., description="Days threshold for critical status")


class ModelFreshnessThresholds(ModelOnexInputState):
    """Configurable thresholds for document freshness assessment."""

    document_type: EnumDocumentType = Field(
        ...,
        description="Document type these thresholds apply to",
    )

    # Freshness score thresholds
    fresh_threshold: float = Field(
        default=0.8,
        description="Minimum score for FRESH status",
    )
    moderate_threshold: float = Field(
        default=0.6,
        description="Minimum score for MODERATE status",
    )
    stale_threshold: float = Field(
        default=0.4,
        description="Minimum score for STALE status",
    )
    # Below stale_threshold = CRITICAL

    # Time-based thresholds (in days)
    max_age_fresh: int = Field(
        default=30,
        description="Maximum age in days for FRESH status",
    )
    max_age_moderate: int = Field(
        default=90,
        description="Maximum age in days for MODERATE status",
    )
    max_age_stale: int = Field(
        default=180,
        description="Maximum age in days for STALE status",
    )

    # Dependency staleness tolerance
    max_stale_dependencies: int = Field(
        default=2,
        description="Maximum stale dependencies before status degradation",
    )
    max_critical_stale_dependencies: int = Field(
        default=0,
        description="Maximum critical stale dependencies allowed",
    )

    # Scoring weights for this document type
    time_decay_weight: float = Field(
        default=0.4,
        description="Weight for time decay in scoring",
    )
    dependency_weight: float = Field(
        default=0.4,
        description="Weight for dependency staleness in scoring",
    )
    semantic_drift_weight: float = Field(
        default=0.2,
        description="Weight for semantic drift in scoring",
    )

    @validator("fresh_threshold", "moderate_threshold", "stale_threshold")
    def validate_score_thresholds(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v

    @validator("time_decay_weight", "dependency_weight", "semantic_drift_weight")
    def validate_scoring_weights(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Scoring weight must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDocumentChange(ModelOnexInputState):
    """Represents a detected change that affects document freshness."""

    change_id: str = Field(..., description="Unique identifier for this change event")
    changed_file_path: str = Field(..., description="Path to the file that changed")
    change_type: str = Field(
        ...,
        description="Type of change (modified, added, deleted, renamed)",
    )
    change_timestamp: datetime = Field(..., description="When the change occurred")

    # Git information if available
    git_commit_hash: str | None = Field(
        None,
        description="Git commit hash if change is from git",
    )
    git_author: str | None = Field(None, description="Git commit author")
    git_message: str | None = Field(None, description="Git commit message")

    # Impact assessment
    affected_documents: list[str] = Field(
        default_factory=list,
        description="Documents potentially affected by this change",
    )
    impact_severity: str = Field(
        default="unknown",
        description="Assessed impact severity (low, medium, high, critical)",
    )
    requires_immediate_review: bool = Field(
        default=False,
        description="Whether this change requires immediate document review",
    )

    # Processing status
    processed: bool = Field(
        default=False,
        description="Whether this change has been processed for freshness updates",
    )
    processed_at: datetime | None = Field(
        None,
        description="When this change was processed",
    )
