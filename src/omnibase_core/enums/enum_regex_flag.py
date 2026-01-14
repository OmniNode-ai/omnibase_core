"""
Supported regex flags for contract-driven NodeCompute.

This module defines the regex flags available for REGEX transformations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRegexFlag(StrValueHelper, str, Enum):
    """
    Supported regex flags.

    Attributes:
        IGNORECASE: Case-insensitive matching.
        MULTILINE: Multi-line mode (^ and $ match line boundaries).
        DOTALL: Dot matches all characters including newlines.
    """

    IGNORECASE = "IGNORECASE"
    MULTILINE = "MULTILINE"
    DOTALL = "DOTALL"


__all__ = ["EnumRegexFlag"]
