"""
Logging Level Enumeration

Standardized logging levels for ONEX architecture.
"""

from enum import Enum


class EnumLoggingLevel(str, Enum):
    """
    Standard logging levels.

    String-based enum that integrates with standard logging frameworks.
    """

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"

    @classmethod
    def get_default_for_environment(cls, environment_name: str) -> "EnumLoggingLevel":
        """Get default logging level for environment."""
        dev_environments = {"development", "dev", "local"}
        if environment_name.lower() in dev_environments:
            return cls.DEBUG
        return cls.INFO

    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled at this level."""
        debug_levels = {self.DEBUG, self.NOTSET}
        return self in debug_levels

    def get_numeric_level(self) -> int:
        """Get numeric logging level for Python logging module."""
        level_mapping = {
            self.CRITICAL: 50,
            self.ERROR: 40,
            self.WARNING: 30,
            self.INFO: 20,
            self.DEBUG: 10,
            self.NOTSET: 0,
        }
        return level_mapping[self]
