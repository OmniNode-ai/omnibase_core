"""
Permission Session Info Model

Type-safe session information for permission validation.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelPermissionSessionInfo(BaseModel):
    """
    Type-safe session information for permission validation.

    Provides structured session data for constraint validation.
    """

    session_id: str = Field(..., description="Unique session identifier")

    user_id: str = Field(..., description="User identifier for the session")

    start_time: datetime = Field(..., description="Session start time")

    last_activity: datetime = Field(..., description="Last activity timestamp")

    ip_address: str = Field(..., description="Client IP address")

    user_agent: Optional[str] = Field(None, description="Client user agent string")

    authentication_method: str = Field(
        "password",
        description="How user authenticated",
        pattern="^(password|sso|certificate|api_key|oauth|mfa)$",
    )

    mfa_verified: bool = Field(
        False, description="Whether MFA was verified in this session"
    )

    mfa_verified_at: Optional[datetime] = Field(
        None, description="When MFA was verified"
    )

    location: Optional[str] = Field(None, description="Geographic location of session")

    device_id: Optional[str] = Field(None, description="Device identifier")

    device_trust_level: str = Field(
        "unknown",
        description="Device trust level",
        pattern="^(trusted|known|unknown|suspicious)$",
    )

    session_flags: List[str] = Field(
        default_factory=list,
        description="Special session flags (e.g., 'elevated', 'readonly')",
    )

    permission_cache: List[str] = Field(
        default_factory=list, description="Cached permissions for this session"
    )

    expires_at: Optional[datetime] = Field(None, description="Session expiration time")
