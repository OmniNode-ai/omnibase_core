"""Sentiment classification for text analysis."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSentiment(StrValueHelper, str, Enum):
    """Sentiment classification for customer communications.

    Used to categorize the emotional tone of support tickets
    and other customer interactions for prioritization and routing.
    """

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


__all__ = ["EnumSentiment"]
