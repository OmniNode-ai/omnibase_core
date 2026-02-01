"""Intent classification output model.

Domain model for intent classification results. This model represents the output
from classifying user intents, including the primary intent, secondary intents,
and classification metadata.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_intent_category import EnumIntentCategory
from omnibase_core.types.typed_dict_intent_metadata import TypedDictIntentMetadata
from omnibase_core.types.typed_dict_secondary_intent import TypedDictSecondaryIntent


class ModelIntentClassificationOutput(BaseModel):
    """Output model for intent classification operations.

    This model represents the result of classifying intents from content.
    It includes the primary classified intent, any secondary intents detected,
    keywords that contributed to the classification, and metadata about the
    classification operation.

    Attributes:
        success: Whether intent classification succeeded.
        intent_category: Primary intent category detected.
        confidence: Confidence score for the primary intent (0.0 to 1.0).
        keywords: Keywords/features that contributed to the classification decision.
        secondary_intents: List of secondary intents with confidence scores.
        metadata: Additional metadata about the classification.

    Example:
        >>> from omnibase_core.enums.intelligence.enum_intent_category import EnumIntentCategory
        >>> output = ModelIntentClassificationOutput(
        ...     success=True,
        ...     intent_category=EnumIntentCategory.CODE_GENERATION,
        ...     confidence=0.95,
        ...     keywords=["python", "function", "generate"],
        ...     secondary_intents=[
        ...         {"intent_category": "debugging", "confidence": 0.3}
        ...     ]
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success: bool = Field(
        ...,
        description="Whether intent classification succeeded",
    )
    intent_category: EnumIntentCategory = Field(
        default=EnumIntentCategory.UNKNOWN,
        description="Primary intent category (see EnumIntentCategory for valid values)",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the primary intent (0.0 to 1.0)",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords/features extracted from the content that contributed to "
        "the classification decision (e.g., 'error', 'traceback' for debugging intent)",
    )
    secondary_intents: list[TypedDictSecondaryIntent] = Field(
        default_factory=list,
        description="List of secondary intents with confidence scores. Uses TypedDictSecondaryIntent "
        "with total=False, allowing any subset of typed fields per entry.",
    )
    metadata: TypedDictIntentMetadata | None = Field(
        default=None,
        description="Additional metadata about the classification. Uses TypedDictIntentMetadata "
        "with total=False, allowing any subset of typed fields.",
    )

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if the primary intent has high confidence.

        Args:
            threshold: Confidence threshold to consider as high (default 0.8).

        Returns:
            True if confidence is at or above the threshold.
        """
        return self.confidence >= threshold

    def get_all_intents(self) -> list[tuple[str, float]]:
        """Get all intents with their confidence scores.

        Returns a list of tuples containing intent category (as string) and confidence,
        starting with the primary intent followed by secondary intents.

        Returns:
            List of (intent_category, confidence) tuples. All categories are strings.
        """
        intents: list[tuple[str, float]] = [
            (self.intent_category.value, self.confidence)
        ]
        for secondary in self.secondary_intents:
            category = secondary.get("intent_category", "unknown")
            conf = secondary.get("confidence", 0.0)
            intents.append((category, conf))
        return intents


__all__ = [
    "EnumIntentCategory",
    "ModelIntentClassificationOutput",
    "TypedDictIntentMetadata",
    "TypedDictSecondaryIntent",
]
