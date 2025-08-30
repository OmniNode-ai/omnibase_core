"""
Debug Level Enum.

Canonical enum for debug verbosity levels used in execution contexts.
"""

from enum import Enum


class EnumDebugLevel(str, Enum):
    """Debug verbosity levels for ONEX execution."""

    NONE = "none"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"
    VERBOSE = "verbose"
