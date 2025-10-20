"""Content types in messages."""

from enum import Enum


class EnumContentType(str, Enum):
    """Content types in messages."""

    TEXT = "text"
    IMAGE = "image"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
