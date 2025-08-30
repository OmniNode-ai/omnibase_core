"""
Audit entry model to replace Dict[str, Any] usage for audit trails.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.model.core.model_audit_value import ModelAuditValue


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
        default_factory=datetime.utcnow, description="When the action occurred"
    )
    action: AuditAction = Field(..., description="Action performed")
    action_detail: Optional[str] = Field(
        None, description="Detailed action description"
    )

    # Actor information
    actor_id: Optional[str] = Field(None, description="ID of the actor (user/service)")
    actor_type: Optional[str] = Field(
        None, description="Type of actor (user/service/system)"
    )
    actor_name: Optional[str] = Field(None, description="Human-readable actor name")
    actor_ip: Optional[str] = Field(None, description="Actor IP address")
    actor_user_agent: Optional[str] = Field(None, description="Actor user agent")

    # Target information
    target_type: Optional[str] = Field(None, description="Type of target resource")
    target_id: Optional[str] = Field(None, description="ID of target resource")
    target_name: Optional[str] = Field(None, description="Human-readable target name")
    target_path: Optional[str] = Field(None, description="Path to target resource")

    # Change information
    previous_value: Optional[ModelAuditValue] = Field(
        None, description="Previous state (for updates)"
    )
    new_value: Optional[ModelAuditValue] = Field(
        None, description="New state (for updates)"
    )
    changes_summary: Optional[List[str]] = Field(
        default_factory=list, description="Summary of changes"
    )

    # Result information
    success: bool = Field(True, description="Whether the action succeeded")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[float] = Field(
        None, description="Operation duration in milliseconds"
    )

    # Context and metadata
    session_id: Optional[str] = Field(None, description="Session ID")
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for tracing"
    )
    request_id: Optional[str] = Field(None, description="Request ID")
    environment: Optional[str] = Field(
        None, description="Environment (dev/staging/prod)"
    )
    service_name: Optional[str] = Field(
        None, description="Service that generated the audit"
    )
    service_version: Optional[str] = Field(None, description="Service version")

    # Security and compliance
    risk_score: Optional[float] = Field(None, description="Risk score of the action")
    compliance_tags: Optional[List[str]] = Field(
        default_factory=list, description="Compliance-related tags"
    )
    requires_review: Optional[bool] = Field(
        None, description="Whether this requires manual review"
    )
    reviewed_by: Optional[str] = Field(None, description="Who reviewed this entry")
    review_timestamp: Optional[datetime] = Field(
        None, description="When it was reviewed"
    )

    # Additional context
    additional_context: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Additional context as key-value pairs"
    )

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelAuditEntry":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @field_serializer("timestamp", "review_timestamp")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
