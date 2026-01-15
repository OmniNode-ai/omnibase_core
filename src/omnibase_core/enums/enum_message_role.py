"""
Message role enum for LLM chat conversations.

Provides strongly-typed message roles for chat conversations
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMessageRole(StrValueHelper, str, Enum):
    """Message roles for LLM chat conversations."""

    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


__all__ = ["EnumMessageRole"]
