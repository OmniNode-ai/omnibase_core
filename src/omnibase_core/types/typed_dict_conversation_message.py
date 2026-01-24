"""TypedDict for conversation message structure.

Defines the TypedDictConversationMessage TypedDict for conversation messages
used in intent classification context.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictConversationMessage(TypedDict):
    """Typed structure for a conversation message.

    Represents a single message in a conversation history, used to provide
    context for intent classification.

    Attributes:
        role: The role of the message sender (e.g., "user", "assistant", "system").
        content: The text content of the message.
    """

    role: str
    content: str


__all__ = ["TypedDictConversationMessage"]
