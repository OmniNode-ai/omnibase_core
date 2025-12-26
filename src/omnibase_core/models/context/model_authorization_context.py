# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
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

from pydantic import BaseModel, ConfigDict, Field

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
    token_type: str | None = Field(
        default=None,
        description="Token type (e.g., Bearer)",
    )
    expiry: str | None = Field(
        default=None,
        description="Token expiry timestamp",
    )
    client_id: str | None = Field(
        default=None,
        description="OAuth client ID",
    )
    scope: str | None = Field(
        default=None,
        description="OAuth scope string (space-separated)",
    )
