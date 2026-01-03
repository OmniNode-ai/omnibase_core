"""
ONEX Model: JWT Payload Model

Strongly typed model for JWT payload with proper type safety.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelJWTPayload(BaseModel):
    """Model for JWT token payload."""

    sub: str = Field(default=..., description="Subject (user ID)")
    username: str | None = Field(default=None, description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    groups: list[str] = Field(default_factory=list, description="User groups")
    session_id: UUID | None = Field(default=None, description="Session ID")
    iat: int | None = Field(default=None, description="Issued at timestamp")
    exp: int | None = Field(default=None, description="Expiration timestamp")
    iss: str | None = Field(default=None, description="Issuer")
    mfa_verified: bool | None = Field(
        default=None, description="MFA verification status"
    )

    @classmethod
    def from_jwt_dict(cls, payload_dict: SerializedDict) -> "ModelJWTPayload":
        """Create payload model from JWT dictionary.

        Args:
            payload_dict: Raw JWT payload dictionary

        Returns:
            Typed JWT payload model
        """
        # Extract and type-narrow values from the dictionary
        sub = payload_dict.get("sub", "")
        username = payload_dict.get("username")
        roles = payload_dict.get("roles", [])
        permissions = payload_dict.get("permissions", [])
        groups = payload_dict.get("groups", [])
        session_id = payload_dict.get("session_id")
        iat = payload_dict.get("iat")
        exp = payload_dict.get("exp")
        iss = payload_dict.get("iss")
        mfa_verified = payload_dict.get("mfa_verified")

        return cls(
            sub=str(sub) if sub else "",
            username=str(username) if isinstance(username, str) else None,
            roles=[str(r) for r in roles] if isinstance(roles, list) else [],
            permissions=[str(p) for p in permissions]
            if isinstance(permissions, list)
            else [],
            groups=[str(g) for g in groups] if isinstance(groups, list) else [],
            session_id=session_id if isinstance(session_id, UUID) else None,
            iat=int(iat) if isinstance(iat, (int, float)) else None,
            exp=int(exp) if isinstance(exp, (int, float)) else None,
            iss=str(iss) if isinstance(iss, str) else None,
            mfa_verified=bool(mfa_verified) if isinstance(mfa_verified, bool) else None,
        )
