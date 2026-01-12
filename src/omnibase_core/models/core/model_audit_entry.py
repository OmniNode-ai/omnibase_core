from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.types import SerializedDict

"""
Audit entry model to replace Dict[str, Any] usage for audit trails.
"""

from omnibase_core.enums.enum_audit_action import EnumAuditAction
from omnibase_core.models.core.model_audit_value import ModelAuditValue
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelAuditEntry(BaseModel):
    """
    Audit trail entry with typed fields.

    Replaces Dict[str, Any] for audit trail entries.

    This model is frozen (immutable) and hashable, suitable for use as dict keys
    or in sets for deduplication and caching purposes.
    """

    # Core audit fields
    audit_id: UUID = Field(default=..., description="Unique audit entry ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the action occurred",
    )
    action: EnumAuditAction = Field(default=..., description="Action performed")
    action_detail: str | None = Field(
        default=None,
        description="Detailed action description",
    )

    # Actor information
    actor_id: UUID | None = Field(
        default=None, description="ID of the actor (user/service)"
    )
    actor_type: str | None = Field(
        default=None,
        description="Type of actor (user/service/system)",
    )
    actor_name: str | None = Field(
        default=None, description="Human-readable actor name"
    )
    actor_ip: str | None = Field(default=None, description="Actor IP address")
    actor_user_agent: str | None = Field(default=None, description="Actor user agent")

    # Target information
    target_type: str | None = Field(default=None, description="Type of target resource")
    target_id: UUID | None = Field(default=None, description="ID of target resource")
    target_name: str | None = Field(
        default=None, description="Human-readable target name"
    )
    target_path: str | None = Field(default=None, description="Path to target resource")

    # Change information
    previous_value: ModelAuditValue | None = Field(
        default=None,
        description="Previous state (for updates)",
    )
    new_value: ModelAuditValue | None = Field(
        default=None,
        description="New state (for updates)",
    )
    changes_summary: list[str] | None = Field(
        default_factory=list,
        description="Summary of changes",
    )

    # Result information
    success: bool = Field(default=True, description="Whether the action succeeded")
    error_code: str | None = Field(default=None, description="Error code if failed")
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    duration_ms: float | None = Field(
        default=None,
        description="Operation duration in milliseconds",
    )

    # Context and metadata
    session_id: UUID | None = Field(default=None, description="Session ID")
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracing",
    )
    request_id: UUID | None = Field(default=None, description="Request ID")
    environment: str | None = Field(
        default=None,
        description="Environment (dev/staging/prod)",
    )
    service_name: str | None = Field(
        default=None,
        description="Service that generated the audit",
    )
    service_version: ModelSemVer | None = Field(
        default=None, description="Service version"
    )

    # Security and compliance
    risk_score: float | None = Field(
        default=None, description="Risk score of the action"
    )
    compliance_tags: list[str] | None = Field(
        default_factory=list,
        description="Compliance-related tags",
    )
    requires_review: bool | None = Field(
        default=None,
        description="Whether this requires manual review",
    )
    reviewed_by: str | None = Field(default=None, description="Who reviewed this entry")
    review_timestamp: datetime | None = Field(
        default=None,
        description="When it was reviewed",
    )

    # Additional context
    additional_context: dict[str, str] | None = Field(
        default_factory=dict,
        description="Additional context as key-value pairs",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @classmethod
    def from_dict(cls, data: SerializedDict) -> "ModelAuditEntry":
        """Create from dictionary for easy migration."""
        return cls.model_validate(data)

    @field_serializer("timestamp", "review_timestamp")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
