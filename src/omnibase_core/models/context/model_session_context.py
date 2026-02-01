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

import ipaddress
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumAuthenticationMethod
from omnibase_core.utils import create_enum_normalizer

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
            the actual client IP or a forwarded IP from proxies. Security:
            Validate and sanitize before logging to prevent log injection
            attacks. Consider GDPR/privacy implications before storage.
            Supports both IPv4 and IPv6 formats (up to 45 characters).
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
        >>> from uuid import UUID
        >>> from omnibase_core.models.context import ModelSessionContext
        >>>
        >>> # Both string and UUID session_id values are accepted (backward compatible)
        >>> context = ModelSessionContext(
        ...     session_id="550e8400-e29b-41d4-a716-446655440000",
        ...     client_ip="192.168.1.100",
        ...     user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        ...     locale="en-US",
        ... )
        >>> isinstance(context.session_id, UUID)
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    session_id: UUID | None = Field(
        default=None,
        description="Session identifier",
    )
    client_ip: str | None = Field(
        default=None,
        description=(
            "Client IP address. Security: Validate/sanitize before logging to prevent "
            "log injection. Consider GDPR/privacy implications for storage. Supports "
            "both IPv4 and IPv6 (up to 45 chars)."
        ),
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
    authentication_method: EnumAuthenticationMethod | str | None = Field(
        default=None,
        description=(
            "Authentication method used (e.g., oauth2, saml, basic). "
            "Accepts EnumAuthenticationMethod values or strings."
        ),
    )

    @field_validator("session_id", mode="before")
    @classmethod
    def coerce_session_id(cls, v: UUID | str | None) -> UUID | None:
        """Coerce string UUID values to UUID type.

        This validator ensures flexible input handling by accepting both UUID objects
        and valid UUID strings. String inputs are automatically converted to UUID,
        enabling seamless interoperability with APIs that return string representations.

        Accepts UUID objects directly or valid UUID string representations.

        Args:
            v: The session ID value, either as UUID, string, or None.

        Returns:
            The UUID value, or None if input is None.

        Raises:
            ValueError: If the string value is not a valid UUID format.
        """
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(
                    f"Invalid UUID string for session_id: '{v}'. "
                    f"Must be a valid UUID format (e.g., '550e8400-e29b-41d4-a716-446655440000')"
                ) from None
        # error-ok: Pydantic field_validator requires ValueError
        raise ValueError(f"session_id must be UUID or str, got {type(v).__name__}")

    @field_validator("authentication_method", mode="before")
    @classmethod
    def normalize_authentication_method(
        cls, v: EnumAuthenticationMethod | str | None
    ) -> EnumAuthenticationMethod | str | None:
        """Normalize authentication method from string or enum input.

        Args:
            v: The authentication method value, either as EnumAuthenticationMethod,
               string, or None.

        Returns:
            The normalized value - EnumAuthenticationMethod if valid enum value,
            otherwise the original string for extensibility.
        """
        return create_enum_normalizer(EnumAuthenticationMethod)(v)

    @field_validator("client_ip", mode="before")
    @classmethod
    def validate_client_ip(cls, v: str | None) -> str | None:
        """Validate that client_ip is a valid IPv4 or IPv6 address.

        Args:
            v: The IP address string to validate, or None.

        Returns:
            The validated IP address string, or None if input is None.

        Raises:
            ValueError: If the value is not a string or not a valid IPv4 or IPv6 address.
        """
        if v is None:
            return None
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"client_ip must be a string, got {type(v).__name__}")
        try:
            # ipaddress.ip_address() handles both IPv4 and IPv6
            ip = ipaddress.ip_address(v)
            return str(ip)
        except ValueError as e:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid IP address '{v}': must be a valid IPv4 or IPv6 address"
            ) from e
