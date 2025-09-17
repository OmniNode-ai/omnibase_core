"""
Provider type enum for LLM provider classification.

Provides strongly-typed provider types for routing and privacy decisions
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumProviderType(str, Enum):
    """LLM provider types for routing and privacy."""

    LOCAL = "local"
    EXTERNAL_TRUSTED = "external_trusted"
    EXTERNAL_UNTRUSTED = "external_untrusted"
