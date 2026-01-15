"""
Input/Output Type Enum.

Strongly typed input/output type values for configuration.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumIoType(StrValueHelper, str, Enum):
    """Strongly typed input/output type values."""

    INPUT = "input"
    OUTPUT = "output"
    CONFIGURATION = "configuration"
    METADATA = "metadata"
    PARAMETERS = "parameters"


# Export for use
__all__ = ["EnumIoType"]
