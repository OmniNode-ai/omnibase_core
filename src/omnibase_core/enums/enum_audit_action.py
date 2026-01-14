"""Audit action types for logging and compliance tracking."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAuditAction(StrValueHelper, str, Enum):
    """Common audit actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    RESTORE = "restore"
    CUSTOM = "custom"


__all__ = ["EnumAuditAction"]
