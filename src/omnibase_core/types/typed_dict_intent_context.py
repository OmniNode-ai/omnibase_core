"""TypedDict for intent classification context.

Defines the TypedDictIntentContext TypedDict for providing additional context
during intent classification operations.
"""

from __future__ import annotations

from typing import TypedDict

from omnibase_core.types.typed_dict_conversation_message import (
    TypedDictConversationMessage,
)


class TypedDictIntentContext(TypedDict, total=False):
    """Typed structure for intent classification context.

    Provides stronger typing for common context fields. With total=False,
    all fields are optional, allowing any subset to be provided. Use this
    typed dict for better IDE support and type checking.

    Attributes:
        user_id: Identifier for the user making the request.
        session_id: Session identifier for tracking conversation context.
        request_id: Unique identifier for this specific request.
        previous_intents: List of previously classified intents in the session.
        language: Language code for the content (e.g., "en", "es").
        domain: Domain context for classification (e.g., "customer_support").
        conversation_history: Previous messages in the conversation.
        custom_labels: Custom intent labels to consider during classification.
        confidence_threshold: Minimum confidence score for classification.
        max_intents: Maximum number of intents to return.
        include_confidence_scores: Whether to include confidence scores in output.
        source_system: System that originated the classification request.
        timestamp_utc: UTC timestamp of the request in ISO format.
    """

    # User and session tracking
    # string-id-ok: user_id may be string ID from external systems
    user_id: str
    # string-id-ok: session_id may be string ID from external systems
    session_id: str
    request_id: str

    # Intent classification context
    previous_intents: list[str]
    language: str
    domain: str
    conversation_history: list[TypedDictConversationMessage]

    # Classification parameters
    custom_labels: list[str]
    confidence_threshold: float
    max_intents: int
    include_confidence_scores: bool

    # Source metadata
    source_system: str
    timestamp_utc: str


__all__ = ["TypedDictIntentContext"]
