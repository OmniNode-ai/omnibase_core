#!/usr/bin/env python3
"""
ModelRealTimeLearningFeedback - Real-time learning feedback data structure.

This model represents real-time learning feedback data structures
in the ONEX platform's workflow 6 system integration.
"""

from pydantic import BaseModel, Field

# Type aliases for strong typing
IntelligenceData = dict[
    str,
    str | int | float | bool | list[str] | dict[str, str | int | float],
]


class ModelRealTimeLearningFeedback(BaseModel):
    """Real-time learning feedback data structure."""

    feedback_type: str = Field(
        ...,
        description="Type of feedback (success, error, improvement)",
    )
    source_operation: str = Field(
        ...,
        description="Operation that generated the feedback",
    )
    learning_signal: IntelligenceData = Field(..., description="Learning signal data")
    adaptation_suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested adaptations",
    )
    confidence_score: float = Field(
        default=0.0,
        description="Confidence in the learning signal",
    )
