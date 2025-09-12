"""
Document freshness models for the OmniMemory freshness management system.

These models define structures for tracking document freshness, monitoring
changes, and managing context staleness to ensure only relevant and current
information is injected into conversations.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EnumDocumentFreshnessStatus(str, Enum):
    """Status levels for document freshness."""

    FRESH = "fresh"  # Document is current and reliable
    STALE = "stale"  # Document may be outdated but usable
    DEPRECATED = "deprecated"  # Document is outdated and should not be used
    UNKNOWN = "unknown"  # Freshness status cannot be determined
    ALWAYS_FRESH = "always_fresh"  # Document should always be considered fresh


class EnumDocumentChangeType(str, Enum):
    """Types of changes that can occur to documents."""

    CONTENT_MODIFIED = "content_modified"
    METADATA_UPDATED = "metadata_updated"
    FILE_RENAMED = "file_renamed"
    FILE_MOVED = "file_moved"
    FILE_DELETED = "file_deleted"
    FILE_CREATED = "file_created"
    PERMISSION_CHANGED = "permission_changed"


class EnumFreshnessPolicy(str, Enum):
    """Policies for determining document freshness."""

    TIME_BASED = "time_based"  # Based on modification time and TTL
    CONTENT_HASH = "content_hash"  # Based on content hash changes
    VERSION_BASED = "version_based"  # Based on version numbers
    DEPENDENCY_BASED = "dependency_based"  # Based on dependency changes
    MANUAL = "manual"  # Manually managed freshness


class EnumTrendDirection(str, Enum):
    """Direction of metric trends."""

    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class ModelDocumentFreshness(BaseModel):
    """Model for tracking the freshness status of a document."""

    document_id: str = Field(description="Unique identifier for the document")
    file_path: str = Field(description="Path to the document file")

    # Freshness status
    status: EnumDocumentFreshnessStatus = Field(
        description="Current freshness status of the document",
    )
    freshness_score: float = Field(
        description="Numeric freshness score (0.0=stale, 1.0=fresh)",
    )

    # Timestamp information
    last_modified: datetime = Field(description="When the document was last modified")
    last_checked: datetime = Field(
        default_factory=datetime.utcnow,
        description="When freshness was last checked",
    )
    last_accessed: datetime | None = Field(
        default=None,
        description="When the document was last accessed for context injection",
    )

    # Content tracking
    content_hash: str | None = Field(
        default=None,
        description="Hash of document content for change detection",
    )
    content_size: int | None = Field(
        default=None,
        description="Size of document content in bytes",
    )

    # Freshness policy
    policy: EnumFreshnessPolicy = Field(
        description="Policy used to determine freshness",
    )
    ttl_seconds: int | None = Field(
        default=None,
        description="Time-to-live for this document in seconds",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When this document expires (calculated from TTL)",
    )

    # Dependencies and relationships
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of files this document depends on",
    )
    dependents: list[str] = Field(
        default_factory=list,
        description="List of files that depend on this document",
    )

    # Usage tracking
    injection_count: int = Field(
        default=0,
        description="Number of times this document has been injected",
    )
    success_rate: float = Field(
        default=1.0,
        description="Success rate when this document is used",
    )

    # Override settings
    always_fresh: bool = Field(
        default=False,
        description="Whether this document should always be considered fresh",
    )
    manual_override: EnumDocumentFreshnessStatus | None = Field(
        default=None,
        description="Manual override for freshness status",
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this freshness record was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this freshness record was last updated",
    )


class ModelDocumentChange(BaseModel):
    """Model for tracking changes to documents."""

    change_id: str = Field(description="Unique identifier for this change")
    document_id: str = Field(description="ID of the document that changed")
    file_path: str = Field(description="Path to the changed document")

    # Change details
    change_type: EnumDocumentChangeType = Field(
        description="Type of change that occurred",
    )
    change_description: str = Field(
        description="Human-readable description of the change",
    )

    # Change content
    old_content_hash: str | None = Field(
        default=None,
        description="Content hash before the change",
    )
    new_content_hash: str | None = Field(
        default=None,
        description="Content hash after the change",
    )

    # Timestamp and source
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this change was detected",
    )
    detection_method: str = Field(description="Method used to detect this change")

    # Impact assessment
    impacts_freshness: bool = Field(
        description="Whether this change affects document freshness",
    )
    requires_refresh: bool = Field(
        description="Whether dependent documents need refreshing",
    )

    # Related changes
    cascade_changes: list[str] = Field(
        default_factory=list,
        description="IDs of related changes triggered by this change",
    )


class ModelFreshnessPolicy(BaseModel):
    """Model for freshness policy configuration."""

    policy_id: str = Field(description="Unique identifier for this policy")
    name: str = Field(description="Human-readable name for the policy")
    description: str = Field(description="Description of what this policy does")

    # Policy configuration
    policy_type: EnumFreshnessPolicy = Field(description="Type of freshness policy")

    # Time-based policy settings
    default_ttl_seconds: int | None = Field(
        default=None,
        description="Default TTL for documents under this policy",
    )
    max_age_seconds: int | None = Field(
        default=None,
        description="Maximum age before document is considered stale",
    )

    # File pattern matching
    file_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns this policy applies to",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="File patterns to exclude from this policy",
    )

    # Policy behavior
    check_dependencies: bool = Field(
        default=False,
        description="Whether to check dependency freshness",
    )
    cascade_staleness: bool = Field(
        default=True,
        description="Whether staleness should cascade to dependents",
    )

    # Override settings
    always_fresh_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns for files that should always be fresh",
    )

    # Policy metadata
    enabled: bool = Field(
        default=True,
        description="Whether this policy is currently active",
    )
    priority: int = Field(
        default=100,
        description="Priority when multiple policies match (higher = more priority)",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this policy was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this policy was last updated",
    )


class ModelFreshnessCheckResult(BaseModel):
    """Model for the result of a freshness check operation."""

    check_id: str = Field(description="Unique identifier for this check")
    document_id: str = Field(description="ID of the document that was checked")

    # Check results
    previous_status: EnumDocumentFreshnessStatus = Field(
        description="Document status before the check",
    )
    current_status: EnumDocumentFreshnessStatus = Field(
        description="Document status after the check",
    )
    status_changed: bool = Field(description="Whether the freshness status changed")

    # Freshness metrics
    freshness_score: float = Field(description="Calculated freshness score (0.0-1.0)")
    age_seconds: int = Field(description="Age of the document in seconds")

    # Check details
    policy_applied: str = Field(
        description="ID of the freshness policy that was applied",
    )
    check_method: str = Field(description="Method used for freshness check")

    # Changes detected
    changes_detected: list[ModelDocumentChange] = Field(
        default_factory=list,
        description="Changes detected during this check",
    )

    # Dependencies checked
    dependencies_checked: int = Field(
        default=0,
        description="Number of dependencies that were checked",
    )
    stale_dependencies: int = Field(
        default=0,
        description="Number of dependencies that are stale",
    )

    # Check metadata
    check_duration_ms: float = Field(description="Time taken for the freshness check")
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this check was performed",
    )

    # Actions taken
    actions_required: list[str] = Field(
        default_factory=list,
        description="Actions that need to be taken based on check results",
    )
    refresh_triggered: bool = Field(
        default=False,
        description="Whether a refresh was triggered by this check",
    )


class ModelFreshnessMonitorStatus(BaseModel):
    """Model for the overall status of the freshness monitoring system."""

    # System status
    monitoring_active: bool = Field(
        description="Whether freshness monitoring is active",
    )
    last_scan_completed: datetime | None = Field(
        default=None,
        description="When the last full scan was completed",
    )
    next_scan_scheduled: datetime | None = Field(
        default=None,
        description="When the next scan is scheduled",
    )

    # Document statistics
    total_documents: int = Field(
        description="Total number of documents being monitored",
    )
    fresh_documents: int = Field(description="Number of documents that are fresh")
    stale_documents: int = Field(description="Number of documents that are stale")
    deprecated_documents: int = Field(
        description="Number of documents that are deprecated",
    )

    # Recent activity
    changes_detected_24h: int = Field(
        description="Number of changes detected in the last 24 hours",
    )
    checks_performed_24h: int = Field(
        description="Number of freshness checks performed in last 24 hours",
    )
    refreshes_triggered_24h: int = Field(
        description="Number of refreshes triggered in last 24 hours",
    )

    # System health
    average_freshness_score: float = Field(
        description="Average freshness score across all documents",
    )
    staleness_trend: str = Field(
        description="Trend in staleness over time (improving, degrading, stable)",
    )

    # Performance metrics
    average_check_time_ms: float = Field(
        description="Average time for freshness checks",
    )
    system_load: float = Field(
        description="Current system load for freshness monitoring",
    )

    # Status metadata
    status_generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this status was generated",
    )
