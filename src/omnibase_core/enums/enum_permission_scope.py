"""
Enum for permission scopes.
"""

from enum import Enum, unique


@unique
class EnumPermissionScope(str, Enum):
    """Permission scope levels."""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TEAM = "team"
    USER = "user"
    SERVICE = "service"
    RESOURCE = "resource"
