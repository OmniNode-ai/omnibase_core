"""
Authentication Type Enumeration.

Authentication types for webhook notifications in ONEX infrastructure.
"""

from enum import Enum


class EnumAuthType(str, Enum):
    """Enumeration for authentication types used in webhook communications."""

    # No authentication
    NONE = "NONE"  # No authentication required

    # Standard authentication methods for webhooks
    BEARER = "BEARER"  # Bearer token authentication (OAuth, JWT)
    BASIC = "BASIC"  # Basic authentication (username:password)
    API_KEY_HEADER = "API_KEY_HEADER"  # API key in custom header
