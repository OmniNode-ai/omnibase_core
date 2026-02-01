"""
Finish reason enum for LLM completion status.

Provides strongly-typed finish reasons for LLM completion status
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFinishReason(StrValueHelper, str, Enum):
    """Completion finish reasons for LLM responses."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"


__all__ = ["EnumFinishReason"]
