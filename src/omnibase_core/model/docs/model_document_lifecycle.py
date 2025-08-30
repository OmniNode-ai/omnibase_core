"""
Document lifecycle management models for automated document categorization and state tracking.

Defines data structures for managing document lifecycle states, transitions,
and automated categorization within the ONEX document management system.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field, validator

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class EnumLifecycleAction(str, Enum):
    """Actions that can be taken on documents in lifecycle management."""

    REVIEW_REQUIRED = "review_required"
    MARK_DEPRECATED = "mark_deprecated"
    ARCHIVE = "archive"
    DELETE = "delete"
    UPDATE_CONTENT = "update_content"
    MOVE_TO_LEGACY = "move_to_legacy"
    PROMOTE_TO_CURRENT = "promote_to_current"
    TAG_FOR_BUSINESS_IDEAS = "tag_for_business_ideas"
    REQUEST_MAINTENANCE = "request_maintenance"
    SCHEDULE_REVIEW = "schedule_review"


class EnumLifecycleTransitionReason(str, Enum):
    """Reasons for lifecycle state transitions."""

    STALENESS_DETECTED = "staleness_detected"
    MANUAL_INTERVENTION = "manual_intervention"
    DEPENDENCY_CHANGES = "dependency_changes"
    CONTENT_ANALYSIS = "content_analysis"
    SCHEDULED_REVIEW = "scheduled_review"
    AI_RECOMMENDATION = "ai_recommendation"
    USER_REQUEST = "user_request"
    AUTOMATED_ANALYSIS = "automated_analysis"
    DIRECTORY_CLASSIFICATION = "directory_classification"


class EnumDocumentCategory(str, Enum):
    """Categories for automated document classification."""

    CORE_DOCUMENTATION = "core_documentation"  # Essential system docs
    REFERENCE_MATERIAL = "reference_material"  # API docs, schemas
    TUTORIALS_GUIDES = "tutorials_guides"  # How-to guides, tutorials
    DEVELOPMENT_NOTES = "development_notes"  # Developer logs, notes
    BUSINESS_IDEAS = "business_ideas"  # Future plans, ideas
    LEGACY_CONTENT = "legacy_content"  # Old but potentially useful
    DEPRECATED_CONTENT = "deprecated_content"  # No longer relevant
    CONFIGURATION_DOCS = "configuration_docs"  # Config and setup docs
    TROUBLESHOOTING = "troubleshooting"  # Problem-solving docs
    MEETING_NOTES = "meeting_notes"  # Meeting records
    PERSONAL_NOTES = "personal_notes"  # Individual developer notes


class ModelLifecycleTransition(ModelOnexInputState):
    """Represents a transition between lifecycle states."""

    transition_id: str = Field(..., description="Unique identifier for this transition")
    document_path: str = Field(
        ...,
        description="Path to the document that transitioned",
    )

    # Transition details
    from_state: str = Field(..., description="Previous lifecycle state")
    to_state: str = Field(..., description="New lifecycle state")
    transition_reason: EnumLifecycleTransitionReason = Field(
        ...,
        description="Reason for the transition",
    )

    # Metadata
    triggered_by: str = Field(
        ...,
        description="What triggered this transition (system, user, ai)",
    )
    triggered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When transition occurred",
    )
    confidence_score: float = Field(
        default=1.0,
        description="Confidence in this transition decision",
    )

    # Context
    context_data: dict = Field(
        default_factory=dict,
        description="Additional context for the transition",
    )
    notes: str | None = Field(
        None,
        description="Human-readable notes about the transition",
    )

    # Approval workflow
    requires_approval: bool = Field(
        default=False,
        description="Whether this transition requires human approval",
    )
    approved: bool | None = Field(
        None,
        description="Whether transition was approved",
    )
    approved_by: str | None = Field(None, description="Who approved the transition")
    approved_at: datetime | None = Field(
        None,
        description="When transition was approved",
    )

    @validator("confidence_score")
    def validate_confidence_score(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Confidence score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDocumentLifecycleConfig(ModelOnexInputState):
    """Configuration for document lifecycle management automation."""

    # Automatic transition thresholds
    auto_stale_threshold_days: int = Field(
        default=90,
        description="Days after which docs auto-transition to stale",
    )
    auto_deprecated_threshold_days: int = Field(
        default=365,
        description="Days after which docs auto-transition to deprecated",
    )
    auto_archive_threshold_days: int = Field(
        default=730,
        description="Days after which docs can be auto-archived",
    )

    # Directory-based classification rules
    directory_mappings: dict[str, EnumDocumentCategory] = Field(
        default_factory=lambda: {
            "docs/": EnumDocumentCategory.CORE_DOCUMENTATION,
            "legacy/": EnumDocumentCategory.LEGACY_CONTENT,
            "deprecated/": EnumDocumentCategory.DEPRECATED_CONTENT,
            "business-ideas/": EnumDocumentCategory.BUSINESS_IDEAS,
            "dev-logs/": EnumDocumentCategory.DEVELOPMENT_NOTES,
            "meeting-notes/": EnumDocumentCategory.MEETING_NOTES,
            "troubleshooting/": EnumDocumentCategory.TROUBLESHOOTING,
        },
        description="Mapping of directory patterns to document categories",
    )

    # Lifecycle rules by category
    category_rules: dict[EnumDocumentCategory, dict] = Field(
        default_factory=dict,
        description="Lifecycle rules specific to each document category",
    )

    # AI analysis settings
    enable_ai_lifecycle_analysis: bool = Field(
        default=True,
        description="Enable AI-powered lifecycle analysis",
    )
    ai_analysis_frequency_days: int = Field(
        default=7,
        description="How often to run AI lifecycle analysis",
    )
    ai_confidence_threshold: float = Field(
        default=0.8,
        description="Minimum confidence for AI lifecycle decisions",
    )

    # Notification settings
    notify_on_transitions: bool = Field(
        default=True,
        description="Send notifications on lifecycle transitions",
    )
    notification_recipients: list[str] = Field(
        default_factory=list,
        description="Email/user IDs to notify",
    )

    # Approval requirements
    require_approval_for_deletion: bool = Field(
        default=True,
        description="Require human approval before deletion",
    )
    require_approval_for_deprecation: bool = Field(
        default=False,
        description="Require approval for deprecation",
    )

    @validator("ai_confidence_threshold")
    def validate_ai_confidence_threshold(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "AI confidence threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDocumentLifecycleState(ModelOnexInputState):
    """Current lifecycle state and metadata for a document."""

    document_path: str = Field(..., description="Path to the document")
    current_state: str = Field(..., description="Current lifecycle state")
    category: EnumDocumentCategory = Field(
        ...,
        description="Document category classification",
    )

    # State tracking
    state_since: datetime = Field(
        default_factory=datetime.utcnow,
        description="When document entered current state",
    )
    previous_state: str | None = Field(None, description="Previous lifecycle state")
    state_change_count: int = Field(default=0, description="Number of state changes")

    # Scheduled actions
    next_review_date: datetime | None = Field(
        None,
        description="When document is scheduled for next review",
    )
    pending_actions: list[EnumLifecycleAction] = Field(
        default_factory=list,
        description="Actions pending for this document",
    )

    # Analysis results
    last_ai_analysis: datetime | None = Field(
        None,
        description="When AI last analyzed this document",
    )
    ai_recommended_state: str | None = Field(
        None,
        description="AI-recommended lifecycle state",
    )
    ai_confidence: float | None = Field(
        None,
        description="AI confidence in recommendation",
    )

    # Manual overrides
    manual_override: bool = Field(
        default=False,
        description="Whether lifecycle is manually overridden",
    )
    override_reason: str | None = Field(
        None,
        description="Reason for manual override",
    )
    override_by: str | None = Field(None, description="Who applied the override")
    override_until: datetime | None = Field(
        None,
        description="Until when the override is valid",
    )

    # Metrics
    access_frequency: float = Field(
        default=0.0,
        description="How frequently this document is accessed",
    )
    reference_count: int = Field(
        default=0,
        description="Number of other documents referencing this one",
    )
    importance_score: float = Field(
        default=0.5,
        description="Calculated importance score (0.0-1.0)",
    )

    @validator("ai_confidence", "importance_score")
    def validate_scores(self, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelLifecycleAnalysisResult(ModelOnexInputState):
    """Result of automated lifecycle analysis for a document."""

    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    document_path: str = Field(..., description="Document that was analyzed")
    analysis_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When analysis was performed",
    )

    # Analysis inputs
    document_age_days: int = Field(..., description="Age of document in days")
    last_modified_days_ago: int = Field(..., description="Days since last modification")
    dependency_staleness_score: float = Field(
        ...,
        description="Score indicating dependency staleness",
    )
    access_pattern_score: float = Field(
        ...,
        description="Score based on access patterns",
    )

    # AI analysis (if enabled)
    ai_content_analysis: dict | None = Field(
        None,
        description="AI analysis of document content",
    )
    ai_relevance_score: float | None = Field(
        None,
        description="AI-assessed relevance score",
    )
    ai_quality_score: float | None = Field(
        None,
        description="AI-assessed quality score",
    )

    # Recommendations
    recommended_state: str = Field(..., description="Recommended lifecycle state")
    recommended_actions: list[EnumLifecycleAction] = Field(
        default_factory=list,
        description="Recommended actions to take",
    )
    confidence_score: float = Field(..., description="Confidence in recommendations")

    # Reasoning
    reasoning: list[str] = Field(
        default_factory=list,
        description="Human-readable reasoning for recommendations",
    )
    factors_considered: list[str] = Field(
        default_factory=list,
        description="Factors that influenced the analysis",
    )

    # Next steps
    requires_human_review: bool = Field(
        default=False,
        description="Whether human review is recommended",
    )
    urgency_level: str = Field(
        default="low",
        description="Urgency level (low, medium, high, critical)",
    )
    estimated_effort_hours: float | None = Field(
        None,
        description="Estimated effort to address recommendations",
    )

    @validator(
        "dependency_staleness_score",
        "access_pattern_score",
        "ai_relevance_score",
        "ai_quality_score",
        "confidence_score",
    )
    def validate_scores(self, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelLifecycleBatchOperation(ModelOnexInputState):
    """Batch operation for processing multiple documents through lifecycle management."""

    operation_id: str = Field(
        ...,
        description="Unique identifier for this batch operation",
    )
    operation_type: str = Field(
        ...,
        description="Type of operation (analysis, transition, cleanup)",
    )

    # Scope
    document_paths: list[str] = Field(
        ...,
        description="Documents to process in this batch",
    )
    directory_patterns: list[str] = Field(
        default_factory=list,
        description="Directory patterns to process",
    )

    # Configuration
    config: ModelDocumentLifecycleConfig = Field(
        ...,
        description="Configuration for this batch operation",
    )
    dry_run: bool = Field(
        default=True,
        description="Whether to perform a dry run without making changes",
    )

    # Progress tracking
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When operation started",
    )
    completed_at: datetime | None = Field(
        None,
        description="When operation completed",
    )
    progress_percentage: float = Field(default=0.0, description="Completion percentage")

    # Results
    documents_processed: int = Field(
        default=0,
        description="Number of documents processed",
    )
    documents_modified: int = Field(
        default=0,
        description="Number of documents modified",
    )
    errors_encountered: int = Field(
        default=0,
        description="Number of errors encountered",
    )

    # Detailed results
    processing_results: list[ModelLifecycleAnalysisResult] = Field(
        default_factory=list,
        description="Detailed results for each document",
    )
    error_details: list[dict] = Field(
        default_factory=list,
        description="Details of any errors encountered",
    )

    # Summary
    summary_statistics: dict = Field(
        default_factory=dict,
        description="Summary statistics for the operation",
    )
    recommendations_summary: dict = Field(
        default_factory=dict,
        description="Summary of all recommendations",
    )

    @validator("progress_percentage")
    def validate_progress_percentage(self, v):
        if not 0.0 <= v <= 100.0:
            msg = "Progress percentage must be between 0.0 and 100.0"
            raise ValueError(msg)
        return v
