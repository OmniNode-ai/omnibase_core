"""Context types for execution environment values."""

from enum import Enum, unique


@unique
class EnumContextTypes(str, Enum):
    """Enum for context types used in execution."""

    CONTEXT = "context"
    VARIABLE = "variable"
    ENVIRONMENT = "environment"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"
