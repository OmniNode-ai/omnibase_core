"""
Operation type enumeration for ONEX CLI operations.

Defines standard operation types used in CLI commands
to replace string literals with type-safe enums.
"""

from enum import Enum


class EnumOperationType(str, Enum):
    """
    Standard operation types for CLI operations.

    Used to categorize CLI operations consistently
    and provide type safety for operation handling.
    """

    INFO = "info"
    CONTRACT = "contract"
    HELP = "help"
    EXECUTE = "execute"
    VALIDATE = "validate"
    GENERATE = "generate"
    LIST = "list"
    STATUS = "status"
    WORKFLOW = "workflow"
    INTROSPECT = "introspect"
