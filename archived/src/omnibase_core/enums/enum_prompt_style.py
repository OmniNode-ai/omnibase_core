"""
Prompt style enum for prompt builder tool.

Provides strongly-typed formatting styles for prompt construction
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumPromptStyle(str, Enum):
    """Prompt formatting styles."""

    PLAIN = "plain"
    MARKDOWN = "markdown"
    XML = "xml"
    JSON_INSTRUCTIONS = "json_instructions"
