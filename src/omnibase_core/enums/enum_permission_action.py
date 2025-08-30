"""
Enum for permission actions.
"""

from enum import Enum


class EnumPermissionAction(str, Enum):
    """Permission actions that can be granted."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    DENY = "deny"
    ADMIN = "admin"
    VIEW = "view"
    EDIT = "edit"
    SHARE = "share"
    EXPORT = "export"
    IMPORT = "import"
