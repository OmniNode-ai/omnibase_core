"""
Enum for operational modes for context rules.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRuleMode(StrValueHelper, str, Enum):
    """Operational modes for context rules."""

    SHADOW = "shadow"  # Log only, no actual injection
    CANARY = "canary"  # Apply to subset of operations
    PRODUCTION = "production"  # Full deployment
    DEPRECATED = "deprecated"  # Marked for removal


__all__ = ["EnumRuleMode"]
