"""
Message role enum for LLM chat conversations.

Provides strongly-typed message roles for chat conversations
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumMessageRole(str, Enum):
    """Message roles for LLM chat conversations."""

    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
