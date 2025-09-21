"""
Debug level enumeration for CLI operations.

Defines the different debug levels for CLI execution.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum


class EnumDebugLevel(str, Enum):
    """
    Strongly typed debug level for CLI operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    DEBUG = "debug"  # Maximum verbosity, all debug information
    INFO = "info"  # Normal verbosity, important information only
    WARN = "warn"  # Warnings and errors only
    ERROR = "error"  # Errors only, minimal output

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_verbosity_order(cls) -> list[EnumDebugLevel]:
        """Get debug levels in order of increasing verbosity."""
        return [cls.ERROR, cls.WARN, cls.INFO, cls.DEBUG]

    @classmethod
    def get_severity_order(cls) -> list[EnumDebugLevel]:
        """Get debug levels in order of decreasing severity."""
        return [cls.ERROR, cls.WARN, cls.INFO, cls.DEBUG]

    def is_more_verbose_than(self, other: EnumDebugLevel) -> bool:
        """Check if this level is more verbose than another level."""
        order = self.get_verbosity_order()
        return order.index(self) > order.index(other)

    def includes_level(self, other: EnumDebugLevel) -> bool:
        """Check if this level includes output from another level."""
        if self == other:
            return True
        return self.is_more_verbose_than(other)


# Export for use
__all__ = ["EnumDebugLevel"]