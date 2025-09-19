"""
Authentication method enum for interface configurations.
"""

from enum import Enum


class EnumAuthenticationMethod(str, Enum):
    """Supported authentication methods for interface configurations."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    MUTUAL_TLS = "mutual_tls"
    SAML = "saml"
    KERBEROS = "kerberos"
    LDAP = "ldap"
