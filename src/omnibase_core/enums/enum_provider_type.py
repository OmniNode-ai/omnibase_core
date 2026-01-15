"""
Provider type enum for LLM provider classification.

Provides strongly-typed provider types for routing and privacy decisions
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumProviderType(StrValueHelper, str, Enum):
    """LLM provider types for routing and privacy."""

    LOCAL = "local"
    EXTERNAL_TRUSTED = "external_trusted"
    EXTERNAL_UNTRUSTED = "external_untrusted"


__all__ = ["EnumProviderType"]
