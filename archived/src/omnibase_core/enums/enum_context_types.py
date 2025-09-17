# Enum for context types
# DO NOT EDIT MANUALLY - regenerate using enum generation tools

from enum import Enum


class EnumContextTypes(str, Enum):
    """Enum for context types used in execution."""

    CONTEXT = "context"
    VARIABLE = "variable"
    ENVIRONMENT = "environment"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"
