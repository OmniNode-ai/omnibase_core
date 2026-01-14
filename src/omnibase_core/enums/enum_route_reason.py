"""
Route reason enum for LLM provider selection.

Provides strongly-typed route reasons for provider selection decisions
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRouteReason(StrValueHelper, str, Enum):
    """Reasons for LLM provider selection."""

    BEST_MATCH = "best_match"
    COST_OPTIMIZED = "cost_optimized"
    PRIVACY_REQUIRED = "privacy_required"
    ONLY_AVAILABLE = "only_available"
    FAILOVER = "failover"
    DEFAULT = "default"


__all__ = ["EnumRouteReason"]
