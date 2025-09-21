"""
Example Category Enum.

Strongly typed example category values for configuration.
"""

from __future__ import annotations

from enum import Enum


class EnumExampleCategory(str, Enum):
    """Strongly typed example category values."""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    VALIDATION = "VALIDATION"
    REFERENCE = "REFERENCE"


# Export for use
__all__ = ["EnumExampleCategory"]