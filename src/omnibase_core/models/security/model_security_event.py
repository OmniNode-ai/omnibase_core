"""
ModelSecurityEvent: Security event for audit trails.

This model represents security events logged during envelope processing
for comprehensive audit trails and compliance tracking.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_security_event_status import EnumSecurityEventStatus
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType


class ModelSecurityEvent(BaseModel):
    """Security event for audit trail."""

    event_id: UUID = Field(default=..., description="Unique event identifier")
    event_type: EnumSecurityEventType = Field(
        default=..., description="Type of security event"
    )
    timestamp: datetime = Field(default=..., description="When the event occurred")
    envelope_id: UUID = Field(default=..., description="Associated envelope ID")
    node_id: UUID | None = Field(
        default=None, description="Node that generated the event"
    )
    user_id: UUID | None = Field(default=None, description="User associated with event")
    signature_id: UUID | None = Field(
        default=None, description="Signature ID if applicable"
    )
    algorithm: str | None = Field(default=None, description="Algorithm used")
    key_id: UUID | None = Field(default=None, description="Key identifier")
    reason: str | None = Field(default=None, description="Reason for event")
    status: EnumSecurityEventStatus = Field(default=..., description="Event status")
    verified: bool | None = Field(default=None, description="Verification result")
    signature_count: int | None = Field(
        default=None, description="Number of signatures"
    )
    verified_signatures: int | None = Field(
        default=None, description="Number of verified signatures"
    )
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    user_roles: list[str] = Field(default_factory=list, description="User roles")
    required_roles: list[str] = Field(
        default_factory=list, description="Required roles"
    )
    expected_hash: str | None = Field(default=None, description="Expected hash value")
    actual_hash: str | None = Field(default=None, description="Actual hash value")
    user_clearance: str | None = Field(
        default=None, description="User security clearance"
    )
    required_clearance: str | None = Field(
        default=None, description="Required security clearance"
    )
