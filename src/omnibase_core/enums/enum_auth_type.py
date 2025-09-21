"""
Authentication type enumeration for security operations.

Provides strongly typed authentication type values for security configurations.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum


class EnumAuthType(str, Enum):
    """
    Strongly typed authentication type for security operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    API_KEY = "api_key"
    MTLS = "mtls"
    DIGEST = "digest"
    CUSTOM = "custom"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def requires_credentials(cls, auth_type: EnumAuthType) -> bool:
        """Check if the auth type requires credentials."""
        return auth_type != cls.NONE

    @classmethod
    def is_token_based(cls, auth_type: EnumAuthType) -> bool:
        """Check if the auth type is token-based."""
        return auth_type in {cls.BEARER, cls.OAUTH2, cls.JWT, cls.API_KEY}

    @classmethod
    def is_certificate_based(cls, auth_type: EnumAuthType) -> bool:
        """Check if the auth type is certificate-based."""
        return auth_type == cls.MTLS

    @classmethod
    def supports_refresh(cls, auth_type: EnumAuthType) -> bool:
        """Check if the auth type supports token refresh."""
        return auth_type in {cls.OAUTH2, cls.JWT}


# Export for use
__all__ = ["EnumAuthType"]
