"""
Log levels and severity levels for ONEX.

EnumLogLevel: Based on SPI LogLevel Literal type for consistency
EnumLogLevel: For validation and generation result classification
"""

from enum import Enum


class EnumLogLevel(str, Enum):
    """Log levels enum based on SPI LogLevel Literal type and severity levels for validation."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"
    SUCCESS = "success"
    UNKNOWN = "unknown"