"""Content types in messages."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContentType(StrValueHelper, str, Enum):
    """Content types in messages."""

    TEXT = "text"
    IMAGE = "image"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


__all__ = ["EnumContentType"]
