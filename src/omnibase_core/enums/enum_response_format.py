"""
Response format enum for LLM tools.

Provides strongly-typed response formats for LLM inference
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumResponseFormat(StrValueHelper, str, Enum):
    """LLM response formats."""

    TEXT = "text"
    JSON = "json"


__all__ = ["EnumResponseFormat"]
