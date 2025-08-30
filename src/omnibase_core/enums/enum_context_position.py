"""
Context position enum for prompt builder tool.

Provides strongly-typed position values for context section injection
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumContextPosition(str, Enum):
    """Context section positions."""

    BEFORE = "before"
    AFTER = "after"
    REPLACE = "replace"
