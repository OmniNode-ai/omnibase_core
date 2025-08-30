"""
Logging levels enum for service configuration.
"""

from enum import Enum


class ModelLogLevelEnum(str, Enum):
    """Logging levels for service configuration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
