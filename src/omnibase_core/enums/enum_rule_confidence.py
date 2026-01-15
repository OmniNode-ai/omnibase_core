"""
Enum for confidence levels for learned rules.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRuleConfidence(StrValueHelper, str, Enum):
    """Confidence levels for learned rules."""

    EXPERIMENTAL = "experimental"  # <50% success rate
    LOW = "low"  # 50-70% success rate
    MEDIUM = "medium"  # 70-85% success rate
    HIGH = "high"  # 85-95% success rate
    VERIFIED = "verified"  # >95% success rate with >100 applications


__all__ = ["EnumRuleConfidence"]
