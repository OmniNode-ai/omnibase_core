"""Intent classification input model.

Domain model for intent classification requests. This model represents the input
for classifying user intents from content, with optional context for improved
classification accuracy.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.typed_dict_conversation_message import (
    TypedDictConversationMessage,
)
from omnibase_core.types.typed_dict_intent_context import TypedDictIntentContext


def _empty_intent_context() -> TypedDictIntentContext:
    """Create an empty TypedDictIntentContext.

    Factory function for Pydantic default_factory that provides correct typing.
    """
    return {}


class ModelIntentClassificationInput(BaseModel):
    """Input model for intent classification operations.

    This model represents the input for classifying user intents from content.
    It supports optional context to improve classification accuracy, including
    conversation history, previous intents, and classification parameters.

    Attributes:
        content: The content to classify intent from.
        correlation_id: Optional correlation ID for request tracing.
        context: Additional context for intent classification.

    Example:
        >>> input_model = ModelIntentClassificationInput(
        ...     content="I want to cancel my subscription",
        ...     context={"domain": "customer_support", "language": "en"}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    content: str = Field(
        ...,
        min_length=1,
        description="Content to classify intent from",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracing (UUID format enforced)",
    )
    context: TypedDictIntentContext = Field(
        default_factory=_empty_intent_context,
        description="Additional context for intent classification. Uses TypedDictIntentContext "
        "with total=False, allowing any subset of typed fields.",
    )


__all__ = [
    "ModelIntentClassificationInput",
    "TypedDictConversationMessage",
    "TypedDictIntentContext",
]
