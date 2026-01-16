"""
Authorization context model for access control.

This module provides ModelAuthorizationContext, a typed model for authorization
metadata that replaces untyped dict[str, str] fields. It captures roles,
permissions, OAuth scopes, and token information for access control decisions.

Thread Safety:
    ModelAuthorizationContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.context.model_audit_metadata: Audit trail metadata
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumTokenType
from omnibase_core.utils import create_enum_normalizer

__all__ = ["ModelAuthorizationContext"]


class ModelAuthorizationContext(BaseModel):
    """Authorization context for access control.

    Provides typed authorization information for RBAC (Role-Based Access Control)
    and ABAC (Attribute-Based Access Control) decisions. Supports both traditional
    role/permission models and OAuth 2.0 scopes.

    Attributes:
        roles: List of user roles for RBAC decisions. Roles define coarse-grained
            access levels (e.g., "admin", "user", "readonly").
        permissions: List of fine-grained permissions for ABAC decisions.
            Permissions define specific operations allowed (e.g., "read:nodes",
            "write:config").
        scopes: List of OAuth 2.0 scopes from the access token. Used for
            API access control in OAuth-authenticated requests.
        token_type: Type of authentication token (e.g., "Bearer", "Basic", "API").
        expiry: Token expiration timestamp in ISO 8601 format. Used for
            proactive token refresh and access revocation.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelAuthorizationContext
        >>>
        >>> auth_ctx = ModelAuthorizationContext(
        ...     roles=["admin", "operator"],
        ...     permissions=["read:nodes", "write:nodes", "execute:workflows"],
        ...     scopes=["openid", "profile", "api:full"],
        ...     token_type="Bearer",
        ...     expiry="2025-01-15T12:00:00Z",
        ... )
        >>> "admin" in auth_ctx.roles
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    roles: list[str] = Field(
        default_factory=list,
        description="User roles",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="User permissions",
    )
    scopes: list[str] = Field(
        default_factory=list,
        description="OAuth scopes",
    )
    token_type: EnumTokenType | str | None = Field(
        default=None,
        description="Token type (e.g., Bearer, API, JWT). Accepts EnumTokenType values or strings.",
    )

    @field_validator("token_type", mode="before")
    @classmethod
    def normalize_token_type(
        cls, v: EnumTokenType | str | None
    ) -> EnumTokenType | str | None:
        """Normalize token type from string or enum input.

        Args:
            v: The token type value, either as EnumTokenType, string, or None.

        Returns:
            The normalized value - EnumTokenType if valid enum value,
            otherwise the original string for extensibility.
        """
        return create_enum_normalizer(EnumTokenType)(v)

    expiry: str | None = Field(
        default=None,
        description="Token expiry timestamp",
    )
    client_id: str | None = Field(
        default=None,
        description="OAuth client ID",
    )

    @field_validator("expiry", mode="before")
    @classmethod
    def validate_expiry_iso8601(cls, value: str | None) -> str | None:
        """Validate expiry is in ISO 8601 format.

        Args:
            value: The expiry timestamp string or None.

        Returns:
            The validated timestamp string unchanged, or None.

        Raises:
            ValueError: If the value is not a string or not valid ISO 8601 format.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"expiry must be a string, got {type(value).__name__}")
        try:
            # Python 3.11+ fromisoformat handles 'Z' suffix
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as e:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"Invalid ISO 8601 timestamp for expiry: {value}") from e
        return value
