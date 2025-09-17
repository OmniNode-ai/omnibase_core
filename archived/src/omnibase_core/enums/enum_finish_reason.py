"""
Finish reason enum for LLM completion status.

Provides strongly-typed finish reasons for LLM completion status
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumFinishReason(str, Enum):
    """Completion finish reasons for LLM responses."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
