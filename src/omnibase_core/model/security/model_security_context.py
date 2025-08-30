"""
Security context model for security-related operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelSecurityContext(BaseModel):
    """
    Security context with typed fields.
    Replaces untyped dictionaries for security_context fields with proper typing.
    """

    # User/Principal information
    user_id: Optional[str] = Field(None, description="User identifier")
    username: Optional[str] = Field(None, description="Username")
    service_account: Optional[str] = Field(None, description="Service account")

    # Authentication details
    auth_method: Optional[str] = Field(None, description="Authentication method used")
    auth_timestamp: Optional[datetime] = Field(
        None, description="Authentication timestamp"
    )
    mfa_verified: bool = Field(False, description="MFA verification status")

    # Session information
    session_id: Optional[str] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")

    # Roles and permissions
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(
        default_factory=list, description="Explicit permissions"
    )
    groups: List[str] = Field(default_factory=list, description="User groups")

    # Security tokens
    access_token: Optional[str] = Field(
        None, description="Access token (if applicable)"
    )
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration")

    # Request context
    request_id: Optional[str] = Field(None, description="Request identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier")

    # Additional security attributes
    security_labels: Dict[str, str] = Field(
        default_factory=dict, description="Security labels"
    )
    trust_level: Optional[int] = Field(None, description="Trust level (0-100)")

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Union[str, int, bool, List[str], datetime, None]]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Union[str, int, bool, List[str], datetime, None]]]
    ) -> Optional["ModelSecurityContext"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)

    @field_serializer("auth_timestamp", "token_expires_at")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
