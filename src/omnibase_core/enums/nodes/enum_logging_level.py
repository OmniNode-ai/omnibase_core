"""
Logging level enum for observability configurations.
"""

from enum import Enum


class EnumLoggingLevel(str, Enum):
    """Supported logging levels for observability configurations."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    WARNING = "WARNING"  # Alias for WARN
    ERROR = "ERROR"
    FATAL = "FATAL"
    CRITICAL = "CRITICAL"  # Alias for FATAL
    OFF = "OFF"
