"""TypedDict for intent classification metadata.

Defines the TypedDictIntentMetadata TypedDict for metadata about intent
classification operations.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictIntentMetadata(TypedDict, total=False):
    """Typed structure for intent classification metadata.

    Provides additional information about the classification operation,
    including timing, model information, and raw scores.

    Attributes:
        status: Operation status (e.g., "success", "partial", "failed").
        message: Human-readable status message.
        tracking_url: URL for tracking the classification request.
        classifier_version: Version of the classifier used.
        classification_time_ms: Time taken for classification in milliseconds.
        model_name: Name of the model used for classification.
        token_count: Number of tokens processed.
        threshold_used: Confidence threshold applied during classification.
        raw_scores: Raw confidence scores for all considered intents.
    """

    # Operation status (used by stubs and real implementations)
    status: str
    message: str
    tracking_url: str

    # Classification details
    # string-version-ok: classifier_version is external classifier version string, not ModelSemVer
    classifier_version: str
    classification_time_ms: float
    model_name: str
    token_count: int
    threshold_used: float
    raw_scores: dict[str, float]


__all__ = ["TypedDictIntentMetadata"]
