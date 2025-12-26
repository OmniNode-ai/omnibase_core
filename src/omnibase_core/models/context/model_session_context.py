# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Session context model for user request tracking.

This module provides ModelSessionContext, a typed model for session-related
metadata that replaces untyped dict[str, str] fields. It captures session
identification and client context information for request tracing.

Thread Safety:
    ModelSessionContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_http_request_metadata: HTTP request metadata
    - omnibase_core.models.context.model_authorization_context: Auth context
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelSessionContext"]


class ModelSessionContext(BaseModel):
    """Session context for user requests.

    Provides typed session identification and client context information.
    All fields are optional as session metadata may be partially populated
    depending on the authentication mechanism and client capabilities.

    Attributes:
        session_id: Unique session identifier for tracking user sessions
            across multiple requests.
        client_ip: IP address of the client making the request. May be
            the actual client IP or a forwarded IP from proxies.
        user_agent: User agent string identifying the client application
            (e.g., browser, CLI tool, API client).
        device_fingerprint: Device fingerprint for session binding and
            fraud detection. Usually a hash of device characteristics.
        locale: User locale preference in BCP 47 format (e.g., "en-US",
            "fr-FR") for localization.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelSessionContext
        >>>
        >>> context = ModelSessionContext(
        ...     session_id="sess_abc123",
        ...     client_ip="192.168.1.100",
        ...     user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        ...     locale="en-US",
        ... )
        >>> context.session_id
        'sess_abc123'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    session_id: str | None = Field(
        default=None,
        description="Session identifier",
    )
    client_ip: str | None = Field(
        default=None,
        description="Client IP address",
    )
    user_agent: str | None = Field(
        default=None,
        description="User agent string",
    )
    device_fingerprint: str | None = Field(
        default=None,
        description="Device fingerprint",
    )
    locale: str | None = Field(
        default=None,
        description="User locale (e.g., en-US)",
    )
    authentication_method: str | None = Field(
        default=None,
        description="Authentication method used (e.g., oauth2, saml, basic)",
    )
