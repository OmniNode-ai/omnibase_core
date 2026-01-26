"""Intelligence models for ONEX integration.

This module provides domain models for AI/ML intelligence operations,
including intent classification and pattern extraction. These models are
cross-repo domain nouns designed for sharing between omnibase_core,
omniintelligence, and other ONEX repositories.

Models:
    ModelIntentClassificationInput: Input for intent classification operations.
    ModelIntentClassificationOutput: Output from intent classification operations.
    ModelPatternError: Error encountered during pattern extraction.
    ModelPatternExtractionInput: Input for pattern extraction operations.
    ModelPatternExtractionOutput: Output from pattern extraction operations.
    ModelPatternRecord: Individual extracted pattern record.
    ModelPatternWarning: Warning encountered during pattern extraction.

TypedDicts (from omnibase_core.types):
    TypedDictConversationMessage: TypedDict for conversation message structure.
    TypedDictIntentContext: TypedDict for intent classification context.
    TypedDictSecondaryIntent: TypedDict for secondary intent entries.
    TypedDictIntentMetadata: TypedDict for classification metadata.

Enums (re-exported for convenience):
    EnumPatternKind: Classification of pattern types (architectural, behavioral, etc.).

"""

from omnibase_core.enums import EnumPatternKind
from omnibase_core.models.intelligence.model_intent_classification_input import (
    ModelIntentClassificationInput,
    TypedDictConversationMessage,
    TypedDictIntentContext,
)
from omnibase_core.models.intelligence.model_intent_classification_output import (
    ModelIntentClassificationOutput,
    TypedDictIntentMetadata,
    TypedDictSecondaryIntent,
)
from omnibase_core.models.intelligence.model_pattern_error import ModelPatternError
from omnibase_core.models.intelligence.model_pattern_extraction_input import (
    ModelPatternExtractionInput,
)
from omnibase_core.models.intelligence.model_pattern_extraction_output import (
    ModelPatternExtractionOutput,
)
from omnibase_core.models.intelligence.model_pattern_record import ModelPatternRecord
from omnibase_core.models.intelligence.model_pattern_warning import ModelPatternWarning

__all__ = [
    # Enums (re-exported for convenience)
    "EnumPatternKind",
    # Models - Intent classification
    "ModelIntentClassificationInput",
    "ModelIntentClassificationOutput",
    # Models - Pattern extraction (OMN-1587)
    "ModelPatternError",
    "ModelPatternExtractionInput",
    "ModelPatternExtractionOutput",
    "ModelPatternRecord",
    "ModelPatternWarning",
    # TypedDicts (canonical names)
    "TypedDictConversationMessage",
    "TypedDictIntentContext",
    "TypedDictIntentMetadata",
    "TypedDictSecondaryIntent",
]
