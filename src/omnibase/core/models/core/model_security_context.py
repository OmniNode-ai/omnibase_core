"""
Security Context Model.

Structured security context for action execution.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ModelSecurityContext(BaseModel):
    """Structured security context for action execution."""

    user_id: Optional[str] = Field(
        None, description="User identifier executing the action"
    )
    role: Optional[str] = Field(None, description="User role or permission level")
    authentication_method: Optional[str] = Field(
        None, description="How the user was authenticated"
    )
    permissions: List[str] = Field(
        default_factory=list, description="Specific permissions granted"
    )
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    session_token: Optional[str] = Field(
        None, description="Session or JWT token identifier"
    )
    requires_mfa: bool = Field(
        default=False, description="Whether multi-factor auth is required"
    )
    security_level: str = Field(
        default="standard", description="Security clearance level"
    )

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: str) -> str:
        """Validate security level is from allowed values."""
        allowed_levels = {"public", "standard", "elevated", "restricted", "classified"}
        if v not in allowed_levels:
            raise ValueError(f"Security level must be one of: {allowed_levels}")
        return v
