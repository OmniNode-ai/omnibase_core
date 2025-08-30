"""
ModelSecurityEvent: Security event for audit trails.

This model represents security events logged during envelope processing
for comprehensive audit trails and compliance tracking.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_security_event_status import \
    EnumSecurityEventStatus
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType


class ModelSecurityEvent(BaseModel):
    """Security event for audit trail."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: EnumSecurityEventType = Field(..., description="Type of security event")
    timestamp: datetime = Field(..., description="When the event occurred")
    envelope_id: str = Field(..., description="Associated envelope ID")

    # Event-specific details
    node_id: Optional[str] = Field(None, description="Node that generated the event")
    user_id: Optional[str] = Field(None, description="User associated with event")
    signature_id: Optional[str] = Field(None, description="Signature ID if applicable")

    # Detailed information
    algorithm: Optional[str] = Field(None, description="Algorithm used")
    key_id: Optional[str] = Field(None, description="Key identifier")
    reason: Optional[str] = Field(None, description="Reason for event")

    # Status and results
    status: EnumSecurityEventStatus = Field(..., description="Event status")
    verified: Optional[bool] = Field(None, description="Verification result")
    signature_count: Optional[int] = Field(None, description="Number of signatures")
    verified_signatures: Optional[int] = Field(
        None, description="Number of verified signatures"
    )

    # Error and warning information
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    user_roles: List[str] = Field(default_factory=list, description="User roles")
    required_roles: List[str] = Field(
        default_factory=list, description="Required roles"
    )

    # Hash values for integrity
    expected_hash: Optional[str] = Field(None, description="Expected hash value")
    actual_hash: Optional[str] = Field(None, description="Actual hash value")

    # Clearance information
    user_clearance: Optional[str] = Field(None, description="User security clearance")
    required_clearance: Optional[str] = Field(
        None, description="Required security clearance"
    )

    @classmethod
    def create_authentication_success(
        cls,
        user_id: str,
        username: str,
        roles: List[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "ModelSecurityEvent":
        """Create authentication success event."""
        return cls(
            event_id=str(uuid4()),
            event_type=EnumSecurityEventType.AUTHENTICATION_SUCCESS,
            timestamp=datetime.utcnow(),
            envelope_id="mcp_server",  # Using MCP server as envelope context
            user_id=user_id,
            status=EnumSecurityEventStatus.SUCCESS,
            user_roles=roles,
        )

    @classmethod
    def create_authentication_failed(
        cls,
        reason: str,
        error: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> "ModelSecurityEvent":
        """Create authentication failure event."""
        return cls(
            event_id=str(uuid4()),
            event_type=EnumSecurityEventType.AUTHENTICATION_FAILED,
            timestamp=datetime.utcnow(),
            envelope_id="mcp_server",
            reason=reason,
            status=EnumSecurityEventStatus.FAILED,
            errors=[error] if error else [],
        )

    @classmethod
    def create_authorization_failed(
        cls,
        user_id: str,
        operation: str,
        resource: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
    ) -> "ModelSecurityEvent":
        """Create authorization failure event."""
        return cls(
            event_id=str(uuid4()),
            event_type=EnumSecurityEventType.AUTHORIZATION_FAILED,
            timestamp=datetime.utcnow(),
            envelope_id="mcp_server",
            user_id=user_id,
            reason=f"Insufficient permissions for operation: {operation}",
            status=EnumSecurityEventStatus.FAILED,
            user_roles=roles or [],
        )

    @classmethod
    def create_tool_access(
        cls,
        user_id: str,
        tool_name: str,
        authorized: bool,
        session_id: Optional[str] = None,
    ) -> "ModelSecurityEvent":
        """Create tool access event."""
        return cls(
            event_id=str(uuid4()),
            event_type=EnumSecurityEventType.TOOL_ACCESS,
            timestamp=datetime.utcnow(),
            envelope_id="mcp_server",
            user_id=user_id,
            status=(
                EnumSecurityEventStatus.SUCCESS
                if authorized
                else EnumSecurityEventStatus.FAILED
            ),
            reason=f"Tool access: {tool_name}",
        )


class ModelSecurityEventCollection(BaseModel):
    """Collection of security events for audit trails."""

    events: List[ModelSecurityEvent] = Field(
        default_factory=list, description="List of security events"
    )

    def add_event(self, event: ModelSecurityEvent) -> None:
        """Add a security event to the collection."""
        self.events.append(event)

    def get_recent_events(self, limit: int = 10) -> List[ModelSecurityEvent]:
        """Get the most recent security events."""
        # Sort by timestamp descending and return the most recent
        sorted_events = sorted(self.events, key=lambda e: e.timestamp, reverse=True)
        return sorted_events[:limit]

    def count_events(self) -> int:
        """Get the total number of events in the collection."""
        return len(self.events)

    def get_events_by_type(
        self, event_type: "EnumSecurityEventType"
    ) -> List[ModelSecurityEvent]:
        """Get events of a specific type."""
        return [event for event in self.events if event.event_type == event_type]

    def get_events_by_user(self, user_id: str) -> List[ModelSecurityEvent]:
        """Get events for a specific user."""
        return [event for event in self.events if event.user_id == user_id]
