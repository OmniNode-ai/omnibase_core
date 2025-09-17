"""
Response format enum for LLM tools.

Provides strongly-typed response formats for LLM inference
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumResponseFormat(str, Enum):
    """LLM response formats."""

    TEXT = "text"
    JSON = "json"
