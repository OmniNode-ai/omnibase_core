"""
Audit entry model to replace Dict[str, Any] usage for audit trails.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.core.model_audit_value import ModelAuditValue


class AuditAction(str, Enum):
    """Common audit actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    RESTORE = "restore"
    CUSTOM = "custom"


class ModelAuditEntry(BaseModel):
    """
    Audit trail entry with typed fields.
    Replaces Dict[str, Any] for audit trail entries.
    """

    # Core audit fields
    audit_id: str = Field(..., description="Unique audit entry ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the action occurred",
    )
    action: AuditAction = Field(..., description="Action performed")
    action_detail: str | None = Field(
        None,
        description="Detailed action description",
    )

    # Actor information
    actor_id: str | None = Field(None, description="ID of the actor (user/service)")
    actor_type: str | None = Field(
        None,
        description="Type of actor (user/service/system)",
    )
    actor_name: str | None = Field(None, description="Human-readable actor name")
    actor_ip: str | None = Field(None, description="Actor IP address")
    actor_user_agent: str | None = Field(None, description="Actor user agent")

    # Target information
    target_type: str | None = Field(None, description="Type of target resource")
    target_id: str | None = Field(None, description="ID of target resource")
    target_name: str | None = Field(None, description="Human-readable target name")
    target_path: str | None = Field(None, description="Path to target resource")

    # Change information
    previous_value: ModelAuditValue | None = Field(
        None,
        description="Previous state (for updates)",
    )
    new_value: ModelAuditValue | None = Field(
        None,
        description="New state (for updates)",
    )
    changes_summary: list[str] | None = Field(
        default_factory=lambda: [],
        description="Summary of changes",
    )

    # Result information
    success: bool = Field(True, description="Whether the action succeeded")
    error_code: str | None = Field(None, description="Error code if failed")
    error_message: str | None = Field(None, description="Error message if failed")
    duration_ms: float | None = Field(
        None,
        description="Operation duration in milliseconds",
    )

    # Context and metadata
    session_id: str | None = Field(None, description="Session ID")
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for tracing",
    )
    request_id: str | None = Field(None, description="Request ID")
    environment: str | None = Field(
        None,
        description="Environment (dev/staging/prod)",
    )
    service_name: str | None = Field(
        None,
        description="Service that generated the audit",
    )
    service_version: str | None = Field(None, description="Service version")

    # Security and compliance
    risk_score: float | None = Field(None, description="Risk score of the action")
    compliance_tags: list[str] | None = Field(
        default_factory=lambda: [],
        description="Compliance-related tags",
    )
    requires_review: bool | None = Field(
        None,
        description="Whether this requires manual review",
    )
    reviewed_by: str | None = Field(None, description="Who reviewed this entry")
    review_timestamp: datetime | None = Field(
        None,
        description="When it was reviewed",
    )

    # Additional context
    additional_context: dict[str, str] | None = Field(
        default_factory=lambda: {},
        description="Additional context as key-value pairs",
    )

    model_config = ConfigDict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelAuditEntry":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @field_serializer("timestamp", "review_timestamp")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return None
