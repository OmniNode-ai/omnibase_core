from __future__ import annotations

"""
Output Type Enum.

Strongly typed output type values for configuration and processing.
"""


from enum import Enum, unique


@unique
class EnumOutputType(str, Enum):
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

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

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
