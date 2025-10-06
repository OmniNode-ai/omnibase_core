from typing import Any

from pydantic import Field

from .model_securityeventcollection import ModelSecurityEventCollection

"""
ModelSecurityEvent: Security event for audit trails.

This model represents security events logged during envelope processing
for comprehensive audit trails and compliance tracking.
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_security_event_status import EnumSecurityEventStatus
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType


class ModelSecurityEvent(BaseModel):
    """Security event for audit trail."""

    event_id: str = Field(default=..., description="Unique event identifier")
    event_type: EnumSecurityEventType = Field(
        default=..., description="Type of security event"
    )
    timestamp: datetime = Field(default=..., description="When the event occurred")
    envelope_id: str = Field(default=..., description="Associated envelope ID")

    # Event-specific details
    node_id: str | None = Field(
        default=None, description="Node that generated the event"
    )
    user_id: str | None = Field(default=None, description="User associated with event")
    signature_id: str | None = Field(
        default=None, description="Signature ID if applicable"
    )

    # Detailed information
    algorithm: str | None = Field(default=None, description="Algorithm used")
    key_id: str | None = Field(default=None, description="Key identifier")
    reason: str | None = Field(default=None, description="Reason for event")

    # Status and results
    status: EnumSecurityEventStatus = Field(default=..., description="Event status")
    verified: bool | None = Field(default=None, description="Verification result")
    signature_count: int | None = Field(
        default=None, description="Number of signatures"
    )
    verified_signatures: int | None = Field(
        default=None,
        description="Number of verified signatures",
    )

    # Error and warning information
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    user_roles: list[str] = Field(default_factory=list, description="User roles")
    required_roles: list[str] = Field(
        default_factory=list,
        description="Required roles",
    )

    # Hash values for integrity
    expected_hash: str | None = Field(default=None, description="Expected hash value")
    actual_hash: str | None = Field(default=None, description="Actual hash value")

    # Clearance information
    user_clearance: str | None = Field(
        default=None, description="User security clearance"
    )
    required_clearance: str | None = Field(
        default=None,
        description="Required security clearance",
    )

    # === Factory Methods Removed (Phase 3E) ===
    # ONEX COMPLIANCE: Use Pydantic constructor directly:
    # ModelSecurityEvent(event_id=str(uuid4()), event_type=..., timestamp=datetime.utcnow(), ...)
