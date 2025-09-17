"""
Enum for operational modes for context rules.
"""

from enum import Enum


class EnumRuleMode(str, Enum):
    """Operational modes for context rules."""

    SHADOW = "shadow"  # Log only, no actual injection
    CANARY = "canary"  # Apply to subset of operations
    PRODUCTION = "production"  # Full deployment
    DEPRECATED = "deprecated"  # Marked for removal
