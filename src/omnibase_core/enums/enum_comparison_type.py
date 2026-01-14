"""
Comparison type enumeration for invariant violation details.

Defines how actual values are compared against expected values
when evaluating invariant violations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumComparisonType(StrValueHelper, str, Enum):
    """Types of comparisons for invariant validation."""

    EXACT = "exact"
    """Value must match exactly."""

    PATTERN = "pattern"
    """Value must match regex pattern."""

    RANGE = "range"
    """Value must be within numeric bounds."""

    SCHEMA = "schema"
    """Value must match JSON schema."""

    PRESENCE = "presence"
    """Field must exist (presence check)."""

    CUSTOM = "custom"
    """Custom validation logic."""


__all__ = ["EnumComparisonType"]
