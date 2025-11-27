from pydantic import Field

"\nPermission Session Info Model\n\nType-safe session information for permission validation.\n"
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModelPermissionSessionInfo(BaseModel):
    """
    Type-safe session information for permission validation.

    Provides structured session data for constraint validation.
    """

    session_id: UUID = Field(default=..., description="Unique session identifier")
    user_id: UUID = Field(default=..., description="User identifier for the session")
    start_time: datetime = Field(default=..., description="Session start time")
    last_activity: datetime = Field(default=..., description="Last activity timestamp")
    ip_address: str = Field(default=..., description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent string")
    authentication_method: str = Field(
        default="password",
        description="How user authenticated",
        pattern="^(password|sso|certificate|api_key|oauth|mfa)$",
    )
    mfa_verified: bool = Field(
        default=False, description="Whether MFA was verified in this session"
    )
    mfa_verified_at: datetime | None = Field(
        default=None, description="When MFA was verified"
    )
    location: str | None = Field(
        default=None, description="Geographic location of session"
    )
    device_id: UUID | None = Field(default=None, description="Device identifier")
    device_trust_level: str = Field(
        default="unknown",
        description="Device trust level",
        pattern="^(trusted|known|unknown|suspicious)$",
    )
    session_flags: list[str] = Field(
        default_factory=list,
        description="Special session flags (e.g., 'elevated', 'readonly')",
    )
    permission_cache: list[str] = Field(
        default_factory=list, description="Cached permissions for this session"
    )
    expires_at: datetime | None = Field(
        default=None, description="Session expiration time"
    )
