"""
Authentication Type Enum

Authentication methods supported for webhook notification delivery.
"""

from enum import Enum


class EnumAuthType(str, Enum):
    """
    Authentication types supported for webhook notification delivery.

    Defines the authentication schemes available for securing webhook
    notifications in the ONEX infrastructure.
    """

    BEARER = "bearer"
    BASIC = "basic"
    API_KEY_HEADER = "api_key_header"

    def __str__(self) -> str:
        """Return the string value of the auth type."""
        return self.value

    def is_bearer(self) -> bool:
        """Check if this is bearer token authentication."""
        return self == self.BEARER

    def is_basic(self) -> bool:
        """Check if this is basic authentication."""
        return self == self.BASIC

    def is_api_key_header(self) -> bool:
        """Check if this is API key header authentication."""
        return self == self.API_KEY_HEADER

    def requires_credentials(self) -> bool:
        """Check if this auth type requires credentials."""
        return True  # All auth types require credentials

    def is_secure(self) -> bool:
        """Check if this is a secure authentication method."""
        # All supported methods are considered secure when used with HTTPS
        return True
