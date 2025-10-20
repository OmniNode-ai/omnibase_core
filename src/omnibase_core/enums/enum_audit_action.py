from enum import Enum


class EnumAuditAction(str, Enum):
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
