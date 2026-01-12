"""Authentication method types for session and identity contexts."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAuthenticationMethod(StrValueHelper, str, Enum):
    """Authentication methods supported for session and identity contexts."""

    # No authentication
    NONE = "none"

    # Credential-based methods
    BASIC = "basic"  # Username/password basic authentication
    PASSWORD = "password"  # Password-only authentication

    # Token-based methods
    TOKEN = "token"  # Generic token authentication
    API_KEY = "api_key"  # API key authentication

    # Certificate-based methods
    CERTIFICATE = "certificate"  # X.509 certificate authentication

    # Federated identity methods
    OAUTH2 = "oauth2"  # OAuth 2.0 authentication
    SAML = "saml"  # SAML 2.0 authentication
    SSO = "sso"  # Single Sign-On (generic)

    # Enhanced security methods
    MULTI_FACTOR = "multi_factor"  # Multi-factor authentication (MFA)

    @classmethod
    def is_federated(cls, method: "EnumAuthenticationMethod") -> bool:
        """
        Check if the authentication method is federated (external identity provider).

        Args:
            method: The authentication method to check

        Returns:
            True if federated, False otherwise
        """
        federated_methods = {cls.OAUTH2, cls.SAML, cls.SSO}
        return method in federated_methods

    @classmethod
    def requires_credentials(cls, method: "EnumAuthenticationMethod") -> bool:
        """
        Check if the authentication method requires user credentials.

        Args:
            method: The authentication method to check

        Returns:
            True if credentials are required, False otherwise
        """
        return method != cls.NONE
