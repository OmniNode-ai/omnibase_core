"""
ONEX Model: JWT Payload Model

Strongly typed model for JWT payload with proper type safety.
"""

from pydantic import BaseModel, Field


class ModelJWTPayload(BaseModel):
    """Model for JWT token payload."""

    sub: str = Field(..., description="Subject (user ID)")
    username: str | None = Field(None, description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    groups: list[str] = Field(default_factory=list, description="User groups")
    session_id: str | None = Field(None, description="Session ID")
    iat: int | None = Field(None, description="Issued at timestamp")
    exp: int | None = Field(None, description="Expiration timestamp")
    iss: str | None = Field(None, description="Issuer")
    mfa_verified: bool | None = Field(None, description="MFA verification status")

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
