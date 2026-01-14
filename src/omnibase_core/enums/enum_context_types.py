"""Context types for execution environment values."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContextTypes(StrValueHelper, str, Enum):
    """Enum for context types used in execution."""

    CONTEXT = "context"
    VARIABLE = "variable"
    ENVIRONMENT = "environment"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"


__all__ = ["EnumContextTypes"]
