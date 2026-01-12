"""
Authentication Type Enumeration.

Authentication types for webhook notifications in ONEX infrastructure.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAuthType(StrValueHelper, str, Enum):
    """Enumeration for authentication types used in webhook communications."""

    # No authentication
    NONE = "none"

    # Standard authentication methods
    BASIC = "basic"  # Basic authentication (username:password)
    BEARER = "bearer"  # Bearer token authentication
    OAUTH2 = "oauth2"  # OAuth 2.0 authentication
    JWT = "jwt"  # JWT token authentication
    API_KEY = "api_key"  # API key authentication
    API_KEY_HEADER = "api_key_header"  # API key in header authentication
    MTLS = "mtls"  # Mutual TLS certificate authentication
    DIGEST = "digest"  # Digest authentication
    CUSTOM = "custom"  # Custom authentication method

    @classmethod
    def requires_credentials(cls, auth_type: "EnumAuthType") -> bool:
        """
        Check if the authentication type requires credentials.

        Args:
            auth_type: The authentication type to check

        Returns:
            True if credentials are required, False otherwise
        """
        return auth_type != cls.NONE

    @classmethod
    def is_token_based(cls, auth_type: "EnumAuthType") -> bool:
        """
        Check if the authentication type is token-based.

        Args:
            auth_type: The authentication type to check

        Returns:
            True if token-based, False otherwise
        """
        token_types = {cls.BEARER, cls.OAUTH2, cls.JWT, cls.API_KEY, cls.API_KEY_HEADER}
        return auth_type in token_types

    @classmethod
    def is_certificate_based(cls, auth_type: "EnumAuthType") -> bool:
        """
        Check if the authentication type is certificate-based.

        Args:
            auth_type: The authentication type to check

        Returns:
            True if certificate-based, False otherwise
        """
        return auth_type == cls.MTLS

    @classmethod
    def supports_refresh(cls, auth_type: "EnumAuthType") -> bool:
        """
        Check if the authentication type supports token refresh.

        Args:
            auth_type: The authentication type to check

        Returns:
            True if refresh is supported, False otherwise
        """
        refresh_types = {cls.OAUTH2, cls.JWT}
        return auth_type in refresh_types
