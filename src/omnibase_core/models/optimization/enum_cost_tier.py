"""
Enum for cost tiers.

Defines cost tiers for budget management.
"""

from enum import Enum


class EnumCostTier(str, Enum):
    """Cost tiers for budget management."""

    ECONOMY = "economy"  # < $10/day
    STANDARD = "standard"  # $10-50/day
    PREMIUM = "premium"  # $50-200/day
    ENTERPRISE = "enterprise"  # $200+/day
