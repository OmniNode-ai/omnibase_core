"""
Token Type Enumeration.

Token types for authentication and authorization in ONEX infrastructure.
Used by context models to specify the type of authentication token.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTokenType(StrValueHelper, str, Enum):
    """Enumeration for token types used in authentication contexts."""

    # Standard token types
    BEARER = "bearer"  # Bearer token (OAuth 2.0 access token format)
    BASIC = "basic"  # Basic authentication token (base64 encoded credentials)
    API_KEY = "api_key"  # API key token
    JWT = "jwt"  # JSON Web Token
    OAUTH2 = "oauth2"  # OAuth 2.0 token (generic)

    # Token lifecycle types
    REFRESH = "refresh"  # Refresh token for obtaining new access tokens
    ACCESS = "access"  # Access token for resource authorization
    ID_TOKEN = "id_token"  # OpenID Connect ID token

    @classmethod
    def is_refreshable(cls, token_type: "EnumTokenType") -> bool:
        """
        Check if the token type supports refresh operations.

        Args:
            token_type: The token type to check

        Returns:
            True if the token can be refreshed, False otherwise
        """
        refreshable_types = {cls.OAUTH2, cls.JWT, cls.ACCESS}
        return token_type in refreshable_types

    @classmethod
    def is_identity_token(cls, token_type: "EnumTokenType") -> bool:
        """
        Check if the token type represents identity information.

        Args:
            token_type: The token type to check

        Returns:
            True if the token contains identity claims, False otherwise
        """
        identity_types = {cls.JWT, cls.ID_TOKEN}
        return token_type in identity_types
