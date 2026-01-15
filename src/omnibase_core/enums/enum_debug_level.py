"""
Debug Level Enum.

Canonical enum for debug verbosity levels used in execution contexts.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDebugLevel(StrValueHelper, str, Enum):
    """Debug verbosity levels for ONEX execution."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"

    @classmethod
    def get_verbosity_order(cls) -> list["EnumDebugLevel"]:
        """
        Get debug levels ordered from least to most verbose.

        Returns:
            List of debug levels from least verbose (ERROR) to most verbose (DEBUG)
        """
        return [cls.ERROR, cls.WARN, cls.INFO, cls.DEBUG]

    @classmethod
    def get_severity_order(cls) -> list["EnumDebugLevel"]:
        """
        Get debug levels ordered from most to least severe.

        Returns:
            List of debug levels from most severe (ERROR) to least severe (DEBUG)
        """
        return [cls.ERROR, cls.WARN, cls.INFO, cls.DEBUG]

    def is_more_verbose_than(self, other: "EnumDebugLevel") -> bool:
        """
        Check if this debug level is more verbose than another.

        Args:
            other: The debug level to compare against

        Returns:
            True if this level is more verbose, False otherwise
        """
        verbosity_order = self.get_verbosity_order()
        try:
            self_index = verbosity_order.index(self)
            other_index = verbosity_order.index(other)
            return self_index > other_index
        except ValueError:
            return False

    def includes_level(self, other: "EnumDebugLevel") -> bool:
        """
        Check if this debug level includes another level.

        A level includes another if it is more verbose or equal.
        For example, DEBUG includes all levels, ERROR only includes ERROR.

        Args:
            other: The debug level to check

        Returns:
            True if this level includes the other, False otherwise
        """
        verbosity_order = self.get_verbosity_order()
        try:
            self_index = verbosity_order.index(self)
            other_index = verbosity_order.index(other)
            # A level includes another if it's at the same position or further right
            # (more verbose) in the verbosity order
            return self_index >= other_index
        except ValueError:
            return False
