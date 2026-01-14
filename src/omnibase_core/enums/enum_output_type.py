"""
Output Type Enum.

Strongly typed output type values for configuration and processing.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOutputType(StrValueHelper, str, Enum):
    """
    Strongly typed output type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    STREAM = "stream"
    FILE = "file"
    CONSOLE = "console"
    API = "api"
    DATABASE = "database"

    @classmethod
    def is_persistent(cls, output_type: EnumOutputType) -> bool:
        """Check if the output type provides persistent storage."""
        return output_type in {cls.FILE, cls.DATABASE}

    @classmethod
    def is_real_time(cls, output_type: EnumOutputType) -> bool:
        """Check if the output type supports real-time streaming."""
        return output_type in {cls.STREAM, cls.CONSOLE, cls.API}

    @classmethod
    def supports_interactive(cls, output_type: EnumOutputType) -> bool:
        """Check if the output type supports interactive operations."""
        return output_type in {cls.CONSOLE, cls.API}


# Export for use
__all__ = ["EnumOutputType"]
