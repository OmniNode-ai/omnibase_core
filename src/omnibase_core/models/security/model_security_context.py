"""
Security context model for security-related operations.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelSecurityContext(BaseModel):
    """
    Security context with typed fields.
    Replaces untyped dict[str, Any]ionaries for security_context fields with proper typing.
    """

    user_id: UUID | None = Field(default=None, description="User identifier")
    username: str | None = Field(default=None, description="Username")
    service_account: str | None = Field(default=None, description="Service account")
    auth_method: str | None = Field(
        default=None, description="Authentication method used"
    )
    auth_timestamp: datetime | None = Field(
        default=None, description="Authentication timestamp"
    )
    mfa_verified: bool = Field(default=False, description="MFA verification status")
    session_id: UUID | None = Field(default=None, description="Session identifier")
    ip_address: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="User agent string")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(
        default_factory=list, description="Explicit permissions"
    )
    groups: list[str] = Field(default_factory=list, description="User groups")
    access_token: str | None = Field(
        default=None, description="Access token (if applicable)"
    )
    token_expires_at: datetime | None = Field(
        default=None, description="Token expiration"
    )
    request_id: UUID | None = Field(default=None, description="Request identifier")
    correlation_id: UUID | None = Field(
        default=None, description="Correlation identifier"
    )
    security_labels: dict[str, str] = Field(
        default_factory=dict, description="Security labels"
    )
    trust_level: int | None = Field(default=None, description="Trust level (0-100)")
    model_config = ConfigDict()

    @classmethod
    def from_dict(
        cls, data: dict[str, str | int | bool | list[str] | datetime | None] | None
    ) -> Optional["ModelSecurityContext"]:
        """Create from dict[str, Any]ionary for easy migration."""
        if data is None:
            return None
        from typing import Optional, cast

        return cls.model_validate(cast(dict[str, Any], data))

    @field_serializer("auth_timestamp", "token_expires_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
