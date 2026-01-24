"""Intelligence models for ONEX integration.

This module provides domain models for AI/ML intelligence operations,
including intent classification. These models are cross-repo domain nouns
designed for sharing between omnibase_core, omniintelligence, and other
ONEX repositories.

Models:
    ModelIntentClassificationInput: Input for intent classification operations.
    ModelIntentClassificationOutput: Output from intent classification operations.

TypedDicts (from omnibase_core.types):
    TypedDictConversationMessage: TypedDict for conversation message structure.
    TypedDictIntentContext: TypedDict for intent classification context.
    TypedDictSecondaryIntent: TypedDict for secondary intent entries.
    TypedDictIntentMetadata: TypedDict for classification metadata.

Backward-Compatible Aliases:
    ConversationMessageDict: Alias for TypedDictConversationMessage.
    IntentContextDict: Alias for TypedDictIntentContext.
    SecondaryIntentDict: Alias for TypedDictSecondaryIntent.
    IntentMetadataDict: Alias for TypedDictIntentMetadata.
"""

from omnibase_core.models.intelligence.model_intent_classification_input import (
    ConversationMessageDict,
    IntentContextDict,
    ModelIntentClassificationInput,
    TypedDictConversationMessage,
    TypedDictIntentContext,
)
from omnibase_core.models.intelligence.model_intent_classification_output import (
    IntentMetadataDict,
    ModelIntentClassificationOutput,
    SecondaryIntentDict,
    TypedDictIntentMetadata,
    TypedDictSecondaryIntent,
)

__all__ = [
    # Backward-compatible aliases
    "ConversationMessageDict",
    "IntentContextDict",
    "IntentMetadataDict",
    "SecondaryIntentDict",
    # Models
    "ModelIntentClassificationInput",
    "ModelIntentClassificationOutput",
    # TypedDicts (canonical names)
    "TypedDictConversationMessage",
    "TypedDictIntentContext",
    "TypedDictIntentMetadata",
    "TypedDictSecondaryIntent",
]
