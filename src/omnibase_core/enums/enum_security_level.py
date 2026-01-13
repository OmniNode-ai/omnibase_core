"""
EnumSecurityLevel: Enumeration of security levels.

This enum defines the security levels for secret backends.
"""

from enum import Enum, unique


@unique
class EnumSecurityLevel(Enum):
    """Security levels for secret backends."""

    BASIC = "basic"
    DEVELOPMENT_ONLY = "development_only"
    MEDIUM = "medium"
    PRODUCTION = "production"
    ENTERPRISE = "enterprise"
    NOT_RECOMMENDED = "not_recommended"
