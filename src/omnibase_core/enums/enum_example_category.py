"""
Example Category Enum.

Strongly typed example category values for configuration.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumExampleCategory(StrValueHelper, str, Enum):
    """Strongly typed example category values."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    VALIDATION = "validation"
    REFERENCE = "reference"


# Export for use
__all__ = ["EnumExampleCategory"]
