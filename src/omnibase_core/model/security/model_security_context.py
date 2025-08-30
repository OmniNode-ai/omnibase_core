"""
Security context model for security-related operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelSecurityContext(BaseModel):
    """
    Security context with typed fields.
    Replaces untyped dictionaries for security_context fields with proper typing.
    """

    # User/Principal information
    user_id: str | None = Field(None, description="User identifier")
    username: str | None = Field(None, description="Username")
    service_account: str | None = Field(None, description="Service account")

    # Authentication details
    auth_method: str | None = Field(None, description="Authentication method used")
    auth_timestamp: datetime | None = Field(
        None,
        description="Authentication timestamp",
    )
    mfa_verified: bool = Field(False, description="MFA verification status")

    # Session information
    session_id: str | None = Field(None, description="Session identifier")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="User agent string")

    # Roles and permissions
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(
        default_factory=list,
        description="Explicit permissions",
    )
    groups: list[str] = Field(default_factory=list, description="User groups")

    # Security tokens
    access_token: str | None = Field(
        None,
        description="Access token (if applicable)",
    )
    token_expires_at: datetime | None = Field(None, description="Token expiration")

    # Request context
    request_id: str | None = Field(None, description="Request identifier")
    correlation_id: str | None = Field(None, description="Correlation identifier")

    # Additional security attributes
    security_labels: dict[str, str] = Field(
        default_factory=dict,
        description="Security labels",
    )
    trust_level: int | None = Field(None, description="Trust level (0-100)")

    model_config = ConfigDict()

    def to_dict(self) -> dict[str, str | int | bool | list[str] | datetime | None]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, str | int | bool | list[str] | datetime | None] | None,
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
