"""
Prompt style enum for prompt builder tool.

Provides strongly-typed formatting styles for prompt construction
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPromptStyle(StrValueHelper, str, Enum):
    """Prompt formatting styles."""

    PLAIN = "plain"
    MARKDOWN = "markdown"
    XML = "xml"
    JSON_INSTRUCTIONS = "json_instructions"


__all__ = ["EnumPromptStyle"]
