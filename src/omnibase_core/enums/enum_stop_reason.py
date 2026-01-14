"""
Stop Reason Enum.

Strongly typed enumeration for Anthropic API stop reasons.
Replaces Literal["end_turn", "max_tokens", "stop_sequence"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStopReason(StrValueHelper, str, Enum):
    """
    Strongly typed stop reason discriminators.

    Used for Anthropic API responses to indicate why text generation stopped.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"

    @classmethod
    def is_natural_stop(cls, stop_reason: EnumStopReason) -> bool:
        """Check if the stop reason represents natural completion."""
        return stop_reason == cls.END_TURN

    @classmethod
    def is_forced_stop(cls, stop_reason: EnumStopReason) -> bool:
        """Check if the stop reason represents forced termination."""
        return stop_reason in {cls.MAX_TOKENS, cls.STOP_SEQUENCE}

    @classmethod
    def is_length_limited(cls, stop_reason: EnumStopReason) -> bool:
        """Check if the stop reason is due to length limits."""
        return stop_reason == cls.MAX_TOKENS

    @classmethod
    def is_sequence_triggered(cls, stop_reason: EnumStopReason) -> bool:
        """Check if the stop reason is due to stop sequence."""
        return stop_reason == cls.STOP_SEQUENCE

    @classmethod
    def suggests_truncation(cls, stop_reason: EnumStopReason) -> bool:
        """Check if the stop reason suggests response was truncated."""
        return stop_reason in {cls.MAX_TOKENS}

    @classmethod
    def suggests_completion(cls, stop_reason: EnumStopReason) -> bool:
        """Check if the stop reason suggests natural completion."""
        return stop_reason in {cls.END_TURN, cls.STOP_SEQUENCE}

    @classmethod
    def get_stop_description(cls, stop_reason: EnumStopReason) -> str:
        """Get a human-readable description of the stop reason."""
        descriptions = {
            cls.END_TURN: "Model naturally completed its response",
            cls.MAX_TOKENS: "Response reached maximum token limit",
            cls.STOP_SEQUENCE: "Encountered a configured stop sequence",
        }
        return descriptions.get(stop_reason, "Unknown stop reason")

    @classmethod
    def get_user_action_suggestion(cls, stop_reason: EnumStopReason) -> str:
        """Get suggested user action based on stop reason."""
        suggestions = {
            cls.END_TURN: "Response complete, no action needed",
            cls.MAX_TOKENS: "Consider increasing token limit or asking for continuation",
            cls.STOP_SEQUENCE: "Response stopped at configured sequence, check if complete",
        }
        return suggestions.get(stop_reason, "No specific action suggested")


# Export for use
__all__ = ["EnumStopReason"]
