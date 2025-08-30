"""
ONEX Model: JWT Payload Model

Strongly typed model for JWT payload with proper type safety.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelJWTPayload(BaseModel):
    """Model for JWT token payload."""

    sub: str = Field(..., description="Subject (user ID)")
    username: Optional[str] = Field(None, description="Username")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    groups: List[str] = Field(default_factory=list, description="User groups")
    session_id: Optional[str] = Field(None, description="Session ID")
    iat: Optional[int] = Field(None, description="Issued at timestamp")
    exp: Optional[int] = Field(None, description="Expiration timestamp")
    iss: Optional[str] = Field(None, description="Issuer")
    mfa_verified: Optional[bool] = Field(None, description="MFA verification status")

    @classmethod
    def from_jwt_dict(cls, payload_dict: dict) -> "ModelJWTPayload":
        """Create payload model from JWT dictionary.

        Args:
            payload_dict: Raw JWT payload dictionary

        Returns:
            Typed JWT payload model
        """
        return cls(
            sub=payload_dict.get("sub", ""),
            username=payload_dict.get("username"),
            roles=payload_dict.get("roles", []),
            permissions=payload_dict.get("permissions", []),
            groups=payload_dict.get("groups", []),
            session_id=payload_dict.get("session_id"),
            iat=payload_dict.get("iat"),
            exp=payload_dict.get("exp"),
            iss=payload_dict.get("iss"),
            mfa_verified=payload_dict.get("mfa_verified"),
        )
