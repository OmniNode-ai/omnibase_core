"""
Table alignment enumeration.

Defines alignment options for table columns and content.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTableAlignment(StrValueHelper, str, Enum):
    """
    Enumeration of table alignment options.

    Used for formatting tabular output in CLI and other interfaces.
    """

    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"
    AUTO = "auto"

    @classmethod
    def is_horizontal_alignment(cls, alignment: EnumTableAlignment) -> bool:
        """Check if alignment is for horizontal positioning."""
        return alignment in {cls.LEFT, cls.RIGHT, cls.CENTER, cls.JUSTIFY}

    @classmethod
    def get_default_alignment(cls) -> EnumTableAlignment:
        """Get the default alignment setting."""
        return cls.LEFT

    @classmethod
    def get_numeric_alignment(cls) -> EnumTableAlignment:
        """Get the preferred alignment for numeric data."""
        return cls.RIGHT

    @classmethod
    def get_text_alignment(cls) -> EnumTableAlignment:
        """Get the preferred alignment for text data."""
        return cls.LEFT


# Export the enum
__all__ = ["EnumTableAlignment"]
